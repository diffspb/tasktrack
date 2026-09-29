from app.services.audit_service import change_reason, parse_reason_header


class ChangeReasonMiddleware:
    """Makes the X-Change-Reason header available to audit_service.record() (ADR-018).

    Pure ASGI (not BaseHTTPMiddleware) so SSE streaming responses are untouched.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        raw = dict(scope["headers"]).get(b"x-change-reason")
        token = change_reason.set(parse_reason_header(raw.decode("latin-1") if raw else None))
        try:
            await self.app(scope, receive, send)
        finally:
            change_reason.reset(token)
