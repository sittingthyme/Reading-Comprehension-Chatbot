"""
Study schedule unlocking, session wall-clock lock, and personalized memory updates.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.db.models import F
from django.utils import timezone

from .models import Conversation, Participant, StudySession
from .study_config import get_profile


def participant_from_token(token: Optional[str]) -> Optional[Participant]:
    if not token:
        return None
    t = str(token).strip()
    if not t:
        return None
    return Participant.objects.filter(auth_token=t).first()


def study_now():
    tz_name = getattr(settings, "STUDY_TIMEZONE", "UTC")
    try:
        import zoneinfo

        tz = zoneinfo.ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc
    return timezone.now().astimezone(tz)


def study_start_datetime() -> datetime:
    """Timezone-aware start of the study in the study timezone."""
    tz_name = getattr(settings, "STUDY_TIMEZONE", "UTC")
    try:
        import zoneinfo

        tz = zoneinfo.ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc
    date_str = getattr(settings, "STUDY_START_DATE", "2026-01-01")
    try:
        y, m, d = (int(x) for x in date_str.split("-", 2))
        return datetime(y, m, d, 0, 0, 0, tzinfo=tz)
    except Exception:
        return datetime(2026, 1, 1, 0, 0, 0, tzinfo=tz)


def released_week_index() -> int:
    """
    1-based week index of the last released study week.
    0 = before study start, no weeks released.
    """
    now = study_now()
    start = study_start_datetime()
    if now < start:
        return 0
    delta_days = (now.date() - start.date()).days
    return delta_days // 7 + 1


def total_study_weeks() -> int:
    return max(1, int(getattr(settings, "STUDY_TOTAL_WEEKS", 3)))


def bootstrap_study_sessions(participant: Participant) -> None:
    """Create locked rows for all week/slot combinations if missing."""
    weeks = total_study_weeks()
    to_create: List[StudySession] = []
    existing = set(
        StudySession.objects.filter(participant=participant).values_list(
            "week_index", "slot_index"
        )
    )
    for w in range(1, weeks + 1):
        for s in range(1, 4):
            if (w, s) not in existing:
                to_create.append(
                    StudySession(
                        participant=participant,
                        week_index=w,
                        slot_index=s,
                        status=StudySession.Status.LOCKED,
                    )
                )
    if to_create:
        StudySession.objects.bulk_create(to_create)


def ordered_sessions(participant: Participant):
    return list(
        StudySession.objects.filter(participant=participant).order_by(
            "week_index", "slot_index"
        )
    )


def refresh_session_availability(participant: Participant) -> None:
    """
    Apply calendar week release + strict sequential completion.
    """
    released = released_week_index()
    slots = ordered_sessions(participant)
    prev_all_completed = True

    for ss in slots:
        if ss.status == StudySession.Status.COMPLETED:
            prev_all_completed = True
            continue

        if ss.week_index > released:
            if ss.status not in (
                StudySession.Status.IN_PROGRESS,
                StudySession.Status.COMPLETED,
            ):
                if ss.status == StudySession.Status.AVAILABLE:
                    ss.status = StudySession.Status.LOCKED
                    ss.save(update_fields=["status"])
            prev_all_completed = False
            continue

        if ss.status == StudySession.Status.IN_PROGRESS:
            prev_all_completed = False
            continue

        if prev_all_completed:
            if ss.status == StudySession.Status.LOCKED:
                ss.status = StudySession.Status.AVAILABLE
                ss.save(update_fields=["status"])
            prev_all_completed = False
        else:
            if ss.status == StudySession.Status.AVAILABLE:
                ss.status = StudySession.Status.LOCKED
                ss.save(update_fields=["status"])


def _session_cap_seconds(participant: Participant) -> int:
    profile = get_profile(participant.condition)
    return profile.max_session_wall_minutes * 60


def wall_elapsed_seconds(ss: StudySession) -> float:
    if not ss.started_at or ss.status != StudySession.Status.IN_PROGRESS:
        return 0.0
    return max(0.0, (timezone.now() - ss.started_at).total_seconds())


def is_wall_locked(ss: StudySession, participant: Participant) -> bool:
    if ss.status != StudySession.Status.IN_PROGRESS or not ss.started_at:
        return False
    return wall_elapsed_seconds(ss) >= _session_cap_seconds(participant)


def mark_time_cap_triggered(ss: StudySession) -> None:
    if ss.time_cap_triggered_at:
        return
    ss.time_cap_triggered_at = timezone.now()
    ss.save(update_fields=["time_cap_triggered_at"])


def is_inactivity_locked(ss: StudySession) -> bool:
    threshold = int(getattr(settings, "STUDY_INACTIVITY_SECONDS", 600))
    if threshold <= 0:
        return False
    if ss.status != StudySession.Status.IN_PROGRESS or not ss.last_activity_at:
        return False
    return (timezone.now() - ss.last_activity_at).total_seconds() >= threshold


def chat_should_lock(ss: StudySession, participant: Participant) -> Optional[str]:
    """Return lock reason ('time_cap' | 'inactive_timeout') or None."""
    if ss.status != StudySession.Status.IN_PROGRESS:
        return None
    if is_wall_locked(ss, participant):
        mark_time_cap_triggered(ss)
        return "time_cap"
    if is_inactivity_locked(ss):
        return "inactive_timeout"
    return None


def touch_activity(ss: StudySession) -> None:
    ss.last_activity_at = timezone.now()
    ss.save(update_fields=["last_activity_at"])


def add_active_seconds(ss: StudySession, delta: int) -> None:
    cap = int(getattr(settings, "STUDY_HEARTBEAT_MAX_DELTA_SECONDS", 120))
    delta = max(0, min(delta, cap))
    if delta <= 0:
        return
    StudySession.objects.filter(pk=ss.pk).update(active_seconds=F("active_seconds") + delta)


def seconds_until_wall_lock(ss: StudySession, participant: Participant) -> Optional[int]:
    if ss.status != StudySession.Status.IN_PROGRESS or not ss.started_at:
        return None
    cap = _session_cap_seconds(participant)
    elapsed = wall_elapsed_seconds(ss)
    return max(0, int(cap - elapsed))


def get_current_study_session(participant: Participant) -> Optional[StudySession]:
    ip = (
        StudySession.objects.filter(
            participant=participant, status=StudySession.Status.IN_PROGRESS
        )
        .order_by("week_index", "slot_index")
        .first()
    )
    if ip:
        return ip
    return (
        StudySession.objects.filter(
            participant=participant, status=StudySession.Status.AVAILABLE
        )
        .order_by("week_index", "slot_index")
        .first()
    )


def progress_dict(participant: Participant) -> Dict[str, Any]:
    bootstrap_study_sessions(participant)
    refresh_session_availability(participant)
    profile = get_profile(participant.condition)
    slots = ordered_sessions(participant)
    current = get_current_study_session(participant)
    payload: Dict[str, Any] = {
        "condition": participant.condition,
        "memoryEnabled": profile.memory_enabled,
        "maxSessionMinutes": profile.max_session_wall_minutes,
        "allowCharacterSelection": profile.allow_character_selection,
        "defaultCharacter": profile.default_character,
        "releasedWeekIndex": released_week_index(),
        "sessions": [
            {
                "id": str(s.id),
                "weekIndex": s.week_index,
                "slotIndex": s.slot_index,
                "status": s.status,
            }
            for s in slots
        ],
    }
    if current:
        payload["focusSessionId"] = str(current.id)
        payload["focusWeekIndex"] = current.week_index
        payload["focusSlotIndex"] = current.slot_index
        payload["focusStatus"] = current.status
        payload["showComprehension"] = current.slot_index == 3
        payload["showLikert"] = True
        if current.status == StudySession.Status.IN_PROGRESS:
            sul = seconds_until_wall_lock(current, participant)
            lock_reason = chat_should_lock(current, participant)
            payload["secondsUntilLock"] = sul
            payload["sessionLocked"] = lock_reason is not None
            payload["lockReason"] = lock_reason
            if current.started_at:
                payload["sessionStartedAt"] = current.started_at.isoformat()
        else:
            payload["secondsUntilLock"] = None
            payload["sessionLocked"] = False
            payload["lockReason"] = None
    else:
        payload["focusSessionId"] = None
        payload["message"] = "All scheduled sessions completed."
    return payload


def get_memory_context_for_chat(participant: Participant) -> str:
    profile = get_profile(participant.condition)
    if not profile.memory_enabled:
        return ""
    summary = (participant.memory_summary or "").strip()
    if not summary:
        return ""
    return (
        "\n\nWhat you already know about this reader from earlier sessions "
        f"(stay consistent; do not contradict):\n{summary}\n"
    )


def validate_likert(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    for key in ("rapport", "closeness", "flow"):
        v = data.get(key)
        if not isinstance(v, int) or v < 1 or v > 5:
            return False
    return True


def comprehension_provided(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    for v in data.values():
        if isinstance(v, str) and v.strip():
            return True
        if isinstance(v, (list, dict)) and v:
            return True
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return True
    return False


def merge_conversation_into_memory(participant: Participant, conversation: Conversation) -> None:
    if participant.condition != Participant.Condition.PERSONALIZED:
        return
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        lines = []
        for m in conversation.messages or []:
            role = m.get("sender", "")
            content = (m.get("content") or "")[:500]
            lines.append(f"{role}: {content}")
        transcript = "\n".join(lines)[:8000]
        if not transcript.strip():
            return
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Summarize in 2-4 short sentences what the child shared about their "
                        "reading (books, reactions, interests). No PII beyond what is in the text. "
                        "English or Portuguese is fine."
                    ),
                },
                {"role": "user", "content": transcript},
            ],
            temperature=0.3,
            max_tokens=200,
        )
        chunk = (completion.choices[0].message.content or "").strip()
        if not chunk:
            return
        prev = (participant.memory_summary or "").strip()
        merged = f"{prev}\n\n---\n{chunk}".strip() if prev else chunk
        max_len = int(getattr(settings, "STUDY_MEMORY_MAX_CHARS", 6000))
        if len(merged) > max_len:
            merged = merged[-max_len:]
        participant.memory_summary = merged
        participant.save(update_fields=["memory_summary"])
    except Exception:
        return


def get_study_session_for_conversation(
    conversation_id: str, participant: Participant
) -> Optional[StudySession]:
    return (
        StudySession.objects.filter(
            participant=participant,
            conversation_id=conversation_id,
            status=StudySession.Status.IN_PROGRESS,
        )
        .first()
    )
