import secrets
from urllib.parse import parse_qs

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

CSRF_SESSION_KEY = "csrf_token"
CSRF_HEADER = "x-csrf-token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def get_or_create_csrf_token(request: Request) -> str:
    token = request.session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[CSRF_SESSION_KEY] = token
    return token


class CSRFMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] in SAFE_METHODS:
            await self.app(scope, receive, send)
            return
        if scope["path"] in {"/auth/callback"}:
            await self.app(scope, receive, send)
            return

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        expected = scope.get("session", {}).get(CSRF_SESSION_KEY)
        submitted = headers.get(CSRF_HEADER)
        body = b""

        if not submitted and headers.get("content-type", "").startswith(
            "application/x-www-form-urlencoded"
        ):
            more_body = True
            while more_body:
                message = await receive()
                body += message.get("body", b"")
                more_body = message.get("more_body", False)
            params = parse_qs(body.decode("latin-1"))
            values = params.get("csrf_token")
            submitted = values[0] if values else None

        if not expected or not submitted or not secrets.compare_digest(str(expected), str(submitted)):
            response = JSONResponse({"detail": "CSRF validation failed"}, status_code=403)
            await response(scope, receive, send)
            return

        if body:
            sent = False

            async def replay_receive() -> Message:
                nonlocal sent
                if sent:
                    return {"type": "http.request", "body": b"", "more_body": False}
                sent = True
                return {"type": "http.request", "body": body, "more_body": False}

            await self.app(scope, replay_receive, send)
            return

        await self.app(scope, receive, send)
