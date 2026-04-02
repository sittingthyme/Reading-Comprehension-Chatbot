"""
Study arm configuration: personalized vs generic profiles.

Override via environment variables (see settings.STUDY_*).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Optional

from django.conf import settings

from .models import Participant


@dataclass(frozen=True)
class StudyProfile:
    max_session_wall_minutes: int
    memory_enabled: bool
    allow_character_selection: bool
    default_character: str


def _codes_from_env(name: str) -> FrozenSet[str]:
    raw = getattr(settings, name, "") or ""
    return frozenset(x.strip() for x in raw.split(",") if x.strip())


def resolve_enrollment_code(code: str) -> Optional[str]:
    """
    Return Participant.Condition value ('personalized' | 'generic') or None if invalid.
    """
    if not code or not str(code).strip():
        return None
    normalized = str(code).strip()
    if normalized in _codes_from_env("STUDY_CODES_PERSONALIZED"):
        return Participant.Condition.PERSONALIZED
    if normalized in _codes_from_env("STUDY_CODES_GENERIC"):
        return Participant.Condition.GENERIC
    return None


def get_profile(condition: str) -> StudyProfile:
    if condition == Participant.Condition.PERSONALIZED:
        return StudyProfile(
            max_session_wall_minutes=int(
                getattr(settings, "STUDY_PROFILE_PERSONALIZED_MAX_SESSION_MINUTES", 20)
            ),
            memory_enabled=True,
            allow_character_selection=True,
            default_character=str(
                getattr(settings, "STUDY_PROFILE_PERSONALIZED_DEFAULT_CHARACTER", "default")
            ),
        )
    return StudyProfile(
        max_session_wall_minutes=int(
            getattr(settings, "STUDY_PROFILE_GENERIC_MAX_SESSION_MINUTES", 20)
        ),
        memory_enabled=False,
        allow_character_selection=False,
        default_character=str(
            getattr(settings, "STUDY_PROFILE_GENERIC_DEFAULT_CHARACTER", "default")
        ),
    )


def allowed_character(condition: str, character_key: str) -> bool:
    profile = get_profile(condition)
    if not profile.allow_character_selection:
        return character_key == profile.default_character
    return True
