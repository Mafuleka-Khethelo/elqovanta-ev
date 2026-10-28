"""Consistent API errors.

Every error body has the shape {"detail": {"code", "message", ...}}.
Codes are stable identifiers. Messages are written for a person using the site.
"""

from fastapi import HTTPException


def fail(status: int, code: str, message: str, **extra: object) -> None:
    detail: dict[str, object] = {"code": code, "message": message}
    detail.update(extra)
    raise HTTPException(status_code=status, detail=detail)
