"""
Study API: registration, progress, session lifecycle, heartbeat.
"""
from __future__ import annotations

import json
import secrets
from typing import Optional

from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Conversation, Participant, StudySession
from .study_config import allowed_character, get_profile, resolve_enrollment_code
from .study_credentials import (
    generate_login_code,
    hash_pin,
    normalize_login_code,
    validate_pin_pair,
    verify_pin,
)
from .study_services import (
    add_active_seconds,
    bootstrap_study_sessions,
    chat_should_lock,
    comprehension_provided,
    merge_conversation_into_memory,
    participant_from_token,
    progress_dict,
    refresh_session_availability,
    touch_activity,
    validate_likert,
)


def _bearer_token(request) -> Optional[str]:
    h = request.META.get("HTTP_AUTHORIZATION", "") or ""
    if h.startswith("Bearer "):
        return h[7:].strip()
    return None


def _require_participant(request):
    p = participant_from_token(_bearer_token(request))
    if not p:
        return None, JsonResponse({"error": "Unauthorized"}, status=401)
    return p, None


def _json_body(request) -> dict:
    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return {}


def _register_response_json(participant: Participant) -> dict:
    profile = get_profile(participant.condition)
    return {
        "participantId": str(participant.id),
        "authToken": participant.auth_token,
        "loginCode": participant.login_code or "",
        "condition": participant.condition,
        "maxSessionMinutes": profile.max_session_wall_minutes,
        "memoryEnabled": profile.memory_enabled,
        "allowCharacterSelection": profile.allow_character_selection,
        "defaultCharacter": profile.default_character,
    }


@csrf_exempt
@require_POST
def study_register(request):
    body = _json_body(request)
    code = (body.get("enrollmentCode") or body.get("enrollment_code") or "").strip()
    display_name = (body.get("displayName") or body.get("display_name") or "").strip()[
        :100
    ]
    pin = body.get("pin") or body.get("PIN") or ""
    pin_confirm = body.get("pinConfirm") or body.get("pin_confirm") or ""

    pin_err = validate_pin_pair(pin, pin_confirm)
    if pin_err:
        return JsonResponse({"error": pin_err}, status=400)

    condition = resolve_enrollment_code(code)
    if not condition:
        return JsonResponse({"error": "Invalid enrollment code"}, status=400)

    pin_hash = hash_pin(str(pin).strip())
    participant = None
    for _ in range(24):
        login_code = generate_login_code()
        token = secrets.token_urlsafe(32)
        try:
            with transaction.atomic():
                participant = Participant.objects.create(
                    condition=condition,
                    display_name=display_name,
                    enrollment_code_used=code,
                    auth_token=token,
                    login_code=login_code,
                    pin_hash=pin_hash,
                )
            break
        except IntegrityError:
            continue

    if not participant:
        return JsonResponse({"error": "Could not allocate session"}, status=500)

    bootstrap_study_sessions(participant)
    refresh_session_availability(participant)
    return JsonResponse(_register_response_json(participant))


@csrf_exempt
@require_POST
def study_login(request):
    body = _json_body(request)
    raw_code = body.get("loginCode") or body.get("login_code") or ""
    pin = (body.get("pin") or body.get("PIN") or "").strip()
    normalized = normalize_login_code(raw_code)
    if not normalized or not pin:
        return JsonResponse(
            {"error": "Código ou PIN incorretos."},
            status=400,
        )

    participant = Participant.objects.filter(login_code=normalized).first()
    if not participant or not participant.pin_hash:
        return JsonResponse(
            {"error": "Código ou PIN incorretos."},
            status=401,
        )

    if not verify_pin(pin, participant.pin_hash):
        return JsonResponse(
            {"error": "Código ou PIN incorretos."},
            status=401,
        )

    if getattr(settings, "STUDY_ROTATE_TOKEN_ON_LOGIN", True):
        for _ in range(8):
            new_token = secrets.token_urlsafe(32)
            try:
                participant.auth_token = new_token
                participant.save(update_fields=["auth_token"])
                break
            except IntegrityError:
                continue

    profile = get_profile(participant.condition)
    return JsonResponse(
        {
            "participantId": str(participant.id),
            "authToken": participant.auth_token,
            "loginCode": participant.login_code or normalized,
            "condition": participant.condition,
            "maxSessionMinutes": profile.max_session_wall_minutes,
            "memoryEnabled": profile.memory_enabled,
            "allowCharacterSelection": profile.allow_character_selection,
            "defaultCharacter": profile.default_character,
        }
    )


def study_progress(request):
    if request.method != "GET":
        return JsonResponse({"error": "GET required"}, status=405)
    participant, err = _require_participant(request)
    if err:
        return err
    return JsonResponse(progress_dict(participant))


@csrf_exempt
@require_POST
def study_session_start(request):
    participant, err = _require_participant(request)
    if err:
        return err
    body = _json_body(request)
    sid = body.get("studySessionId") or body.get("study_session_id")
    user_name = (body.get("userName") or participant.display_name or "Participant")[:100]
    character = (body.get("character") or "").strip() or get_profile(
        participant.condition
    ).default_character

    if not allowed_character(participant.condition, character):
        return JsonResponse({"error": "Character not allowed for this study arm"}, status=400)

    bootstrap_study_sessions(participant)
    refresh_session_availability(participant)

    if sid:
        try:
            ss = StudySession.objects.get(id=sid, participant=participant)
        except StudySession.DoesNotExist:
            return JsonResponse({"error": "Study session not found"}, status=404)
    else:
        ss = (
            StudySession.objects.filter(
                participant=participant, status=StudySession.Status.AVAILABLE
            )
            .order_by("week_index", "slot_index")
            .first()
        )
        if not ss:
            return JsonResponse({"error": "No session available to start"}, status=400)

    if ss.status == StudySession.Status.IN_PROGRESS and ss.conversation_id:
        convo = ss.conversation
        return JsonResponse(
            {
                "studySessionId": str(ss.id),
                "conversationId": str(convo.id),
                "character": convo.character,
                "userName": convo.user_name,
                "messages": convo.messages or [],
                "sessionStartedAt": ss.started_at.isoformat() if ss.started_at else None,
            }
        )

    if ss.status != StudySession.Status.AVAILABLE:
        return JsonResponse(
            {"error": "Session is not available to start", "status": ss.status},
            status=400,
        )

    initial_message = body.get("initialMessage")
    messages = []
    if initial_message:
        messages.append(
            {
                "sender": "assistant",
                "content": initial_message,
                "created_at": timezone.now().isoformat(),
                "meta": {"role": "agent", "on_text": True},
            }
        )

    now = timezone.now()
    convo = Conversation.objects.create(
        user_name=user_name,
        character=character,
        messages=messages,
        participant=participant,
    )
    ss.conversation = convo
    ss.status = StudySession.Status.IN_PROGRESS
    ss.started_at = now
    ss.last_activity_at = now
    ss.save(
        update_fields=[
            "conversation",
            "status",
            "started_at",
            "last_activity_at",
        ]
    )

    refresh_session_availability(participant)

    return JsonResponse(
        {
            "studySessionId": str(ss.id),
            "conversationId": str(convo.id),
            "character": character,
            "userName": user_name,
            "messages": convo.messages or [],
            "sessionStartedAt": ss.started_at.isoformat() if ss.started_at else None,
        }
    )


@csrf_exempt
@require_POST
def study_heartbeat(request):
    participant, err = _require_participant(request)
    if err:
        return err
    body = _json_body(request)
    sid = body.get("studySessionId") or body.get("study_session_id")
    delta = int(body.get("activeDeltaSeconds") or body.get("active_delta_seconds") or 0)
    if not sid:
        return JsonResponse({"error": "studySessionId required"}, status=400)
    try:
        ss = StudySession.objects.get(id=sid, participant=participant)
    except StudySession.DoesNotExist:
        return JsonResponse({"error": "Study session not found"}, status=404)

    if ss.status != StudySession.Status.IN_PROGRESS:
        return JsonResponse({"ok": True, "sessionLocked": False})

    touch_activity(ss)
    add_active_seconds(ss, delta)
    lock = chat_should_lock(ss, participant)
    return JsonResponse(
        {
            "ok": True,
            "sessionLocked": lock is not None,
            "lockReason": lock,
        }
    )


@csrf_exempt
@require_POST
def study_session_complete(request):
    participant, err = _require_participant(request)
    if err:
        return err
    body = _json_body(request)
    sid = body.get("studySessionId") or body.get("study_session_id")
    end_reason = (body.get("endReason") or body.get("end_reason") or "completed_content")[
        :40
    ]
    likert = body.get("likert") or body.get("likert_responses")
    comprehension = body.get("comprehension") or body.get("comprehension_responses")

    if not sid:
        return JsonResponse({"error": "studySessionId required"}, status=400)
    try:
        ss = StudySession.objects.get(id=sid, participant=participant)
    except StudySession.DoesNotExist:
        return JsonResponse({"error": "Study session not found"}, status=404)

    if ss.status != StudySession.Status.IN_PROGRESS:
        return JsonResponse(
            {"error": "Session is not in progress", "status": ss.status}, status=400
        )

    if not validate_likert(likert):
        return JsonResponse(
            {"error": "likert must include rapport, closeness, flow (1-5 integers)"},
            status=400,
        )

    if ss.slot_index == 3:
        if not comprehension_provided(comprehension):
            return JsonResponse(
                {"error": "comprehension responses required for session 3 of each week"},
                status=400,
            )

    now = timezone.now()
    ss.status = StudySession.Status.COMPLETED
    ss.ended_at = now
    ss.end_reason = end_reason
    ss.likert_responses = likert
    if ss.slot_index == 3:
        ss.comprehension_responses = comprehension
    ss.save(
        update_fields=[
            "status",
            "ended_at",
            "end_reason",
            "likert_responses",
            "comprehension_responses",
        ]
    )

    if ss.conversation:
        merge_conversation_into_memory(participant, ss.conversation)

    refresh_session_availability(participant)

    return JsonResponse({"ok": True, "progress": progress_dict(participant)})


@csrf_exempt
@require_POST
def study_session_exit(request):
    """Mark intent to finish; client still must call complete with surveys."""
    participant, err = _require_participant(request)
    if err:
        return err
    body = _json_body(request)
    sid = body.get("studySessionId") or body.get("study_session_id")
    if not sid:
        return JsonResponse({"error": "studySessionId required"}, status=400)
    try:
        ss = StudySession.objects.get(id=sid, participant=participant)
    except StudySession.DoesNotExist:
        return JsonResponse({"error": "Study session not found"}, status=404)
    # Optional: store explicit_exit_pending — omitted; complete() sends end_reason
    return JsonResponse({"ok": True, "completeWithEndReason": "explicit_exit"})
