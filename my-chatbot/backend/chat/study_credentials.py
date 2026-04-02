"""
Login code generation and PIN validation for study return login.
"""
from __future__ import annotations

import secrets
from typing import Optional, Tuple

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password

# Unambiguous uppercase alphanumerics (no 0, O, 1, I, L)
LOGIN_CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def generate_login_code(length: int | None = None) -> str:
    n = length or int(getattr(settings, "STUDY_LOGIN_CODE_LENGTH", 10))
    return "".join(secrets.choice(LOGIN_CODE_ALPHABET) for _ in range(n))


def normalize_login_code(raw: str) -> str:
    if not raw:
        return ""
    s = str(raw).upper().replace("-", "").replace(" ", "")
    allowed = set(LOGIN_CODE_ALPHABET)
    return "".join(c for c in s if c in allowed)


def pin_policy() -> Tuple[int, int]:
    lo = int(getattr(settings, "STUDY_PIN_MIN_LENGTH", 4))
    hi = int(getattr(settings, "STUDY_PIN_MAX_LENGTH", 6))
    return lo, hi


def validate_pin_pair(pin: str, pin_confirm: str) -> Optional[str]:
    """Return error message or None if OK."""
    lo, hi = pin_policy()
    p = (pin or "").strip()
    c = (pin_confirm or "").strip()
    if not p.isdigit():
        return "O PIN deve conter apenas algarismos."
    if len(p) < lo or len(p) > hi:
        return f"O PIN deve ter entre {lo} e {hi} algarismos."
    if p != c:
        return "Os PINs não coincidem."
    return None


def hash_pin(plain: str) -> str:
    return make_password(plain)


def verify_pin(plain: str, pin_hash: str) -> bool:
    if not pin_hash:
        return False
    return check_password(plain, pin_hash)
