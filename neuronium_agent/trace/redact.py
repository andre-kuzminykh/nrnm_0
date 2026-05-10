"""Secret redaction utilities."""

from __future__ import annotations

import re
from typing import Any, Dict


_SECRET_KEYS = re.compile(
    r"(api[_-]?key|token|password|secret|authorization|bearer|private[_-]?key)",
    re.IGNORECASE,
)

_INLINE_TOKEN_PATTERN = re.compile(
    r"(sk-[A-Za-z0-9]{8,}|ghp_[A-Za-z0-9]{8,}|AKIA[A-Z0-9]{8,}|Bearer\s+[A-Za-z0-9._-]+)",
    re.IGNORECASE,
)

REDACTED = "***REDACTED***"


def _is_secret_key(key: str) -> bool:
    return bool(_SECRET_KEYS.search(key))


def redact_value(key: str, value: Any) -> Any:
    if _is_secret_key(key):
        return REDACTED
    if isinstance(value, dict):
        return redact_payload(value)
    if isinstance(value, list):
        return [redact_value(key, v) for v in value]
    if isinstance(value, str):
        return _INLINE_TOKEN_PATTERN.sub(REDACTED, value)
    return value


def redact_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return payload
    out: Dict[str, Any] = {}
    for key, value in payload.items():
        out[key] = redact_value(str(key), value)
    return out
