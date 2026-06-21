import secrets
from urllib.parse import parse_qs

from starlette.datastructures import Headers
from starlette.formparsers import MultiPartException, MultiPartParser
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

CSRF_SESSION_KEY = "csrf_token"
CSRF_HEADER = "x-csrf-token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
MAX_CSRF_FORM_BYTES = 6 * 1024 * 1024


class FormBodyTooLargeError(ValueError):
    pass


def get_or_create_csrf_token(request: Request) -> str:
    token = request.session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[CSRF_SESSION_KEY] = token
    return token


async def read_form_body(receive: Receive, limit: int = MAX_CSRF_FORM_BYTES) -> bytes:
    body = b""
    more_body = True
    while more_body:
        message = await receive()
        body += message.get("body", b"")
        if len(body) > limit:
            raise FormBodyTooLargeError
        more_body = message.get("more_body", False)
    return body


async def csrf_token_from_multipart(scope: Scope, body: bytes) -> str | None:
    async def stream():
        yield body

    parser = MultiPartParser(
        Headers(raw=scope.get("headers", [])),
        stream(),
        max_files=2,
        max_fields=50,
        max_part_size=MAX_CSRF_FORM_BYTES,
    )
    form = await parser.parse()
    try:
        value = form.get("csrf_token")
        return str(value) if value is not None else None
    finally:
        await form.close()


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

        content_type = headers.get("content-type", "").lower()
        if not submitted and (
            content_type.startswith("application/x-www-form-urlencoded")
            or content_type.startswith("multipart/form-data")
        ):
            try:
                body = await read_form_body(receive)
            except FormBodyTooLargeError:
                response = JSONResponse({"detail": "Form body too large"}, status_code=413)
                await response(scope, receive, send)
                return
            if content_type.startswith("application/x-www-form-urlencoded"):
                params = parse_qs(body.decode("latin-1"))
                values = params.get("csrf_token")
                submitted = values[0] if values else None
            else:
                try:
                    submitted = await csrf_token_from_multipart(scope, body)
                except MultiPartException:
                    response = JSONResponse({"detail": "Invalid multipart form"}, status_code=400)
                    await response(scope, receive, send)
                    return

        if (
            not expected
            or not submitted
            or not secrets.compare_digest(str(expected), str(submitted))
        ):
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
