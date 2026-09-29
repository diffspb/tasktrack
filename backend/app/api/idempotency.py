"""FastAPI glue for Idempotency-Key (ADR-019, FR-003 TT-04).

- `idempotency_guard` (router dependency): reserves the key in the request
  session before the endpoint runs; releases it if the endpoint raises.
- `IdempotencyResponseMiddleware`: after a successful response, stores it for
  replays. Pure ASGI, so it sees the exact bytes sent.
- `replay_handler`: turns IdempotentReplay into the stored response.
"""
from fastapi import Depends, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_session
from app.models.user import User
from app.services import idempotency_service
from app.services.idempotency_service import MUTATING_METHODS, IdempotentReplay

HEADER = "idempotency-key"
REPLAYED_HEADER = "Idempotent-Replayed"
_STATE = "idempotency"


async def idempotency_guard(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    key = request.headers.get(HEADER)
    if key is None or request.method not in MUTATING_METHODS:
        yield
        return

    path = request.url.path + (f"?{request.url.query}" if request.url.query else "")
    req_hash = idempotency_service.request_hash(request.method, path, await request.body())
    await idempotency_service.reserve(session, user, key, req_hash)
    request.state.idempotency = (user.id, key)
    try:
        yield
    except Exception:
        request.state.idempotency = None
        await idempotency_service.release(session, user.id, key)
        raise


async def replay_handler(request: Request, exc: IdempotentReplay) -> Response:
    return Response(
        content=exc.body, status_code=exc.status_code, media_type=exc.media_type,
        headers={REPLAYED_HEADER: "true"},
    )


class IdempotencyResponseMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in MUTATING_METHODS:
            return await self.app(scope, receive, send)

        captured: dict = {"body": b""}

        async def capture(message):
            if message["type"] == "http.response.start":
                captured["status"] = message["status"]
                headers = dict(message.get("headers") or [])
                captured["media_type"] = (headers.get(b"content-type") or b"").decode() or None
            elif message["type"] == "http.response.body":
                captured["body"] += message.get("body", b"")
            await send(message)

        await self.app(scope, receive, capture)

        reservation = scope.get("state", {}).get(_STATE)
        if reservation and 200 <= captured.get("status", 0) < 300:
            user_id, key = reservation
            async for session in _new_session(scope["app"]):
                await idempotency_service.complete(
                    session, user_id, key, captured["status"], captured["body"], captured["media_type"],
                )


def _new_session(app):
    # Honour dependency overrides so tests store the response in their own session.
    factory = app.dependency_overrides.get(get_session, get_session)
    return factory()
