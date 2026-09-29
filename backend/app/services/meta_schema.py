"""Task.meta validation against the task type's JSON Schema (ADR-023, FR-003 TT-13)."""
from fastapi import HTTPException, status
from jsonschema import Draft202012Validator

_MAX_ERRORS = 20


def validate_meta(schema: dict | None, meta: dict) -> None:
    if not schema:
        return
    errors = sorted(Draft202012Validator(schema).iter_errors(meta), key=lambda e: list(e.absolute_path))
    if errors:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, {
            "code": "META_INVALID",
            "errors": [
                {"path": ".".join(str(p) for p in e.absolute_path), "message": e.message}
                for e in errors[:_MAX_ERRORS]
            ],
        })


def missing_fields(required: list[str], meta: dict) -> list[str]:
    """Required meta keys that are absent or empty."""
    return [f for f in required if meta.get(f) in (None, "", [], {})]
