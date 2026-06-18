from collections import defaultdict, deque
from time import monotonic
from typing import Deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60
        self._hits: dict[str, Deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path.startswith("/static"):
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        now = monotonic()
        hits = self._hits[client]
        while hits and now - hits[0] > self.window_seconds:
            hits.popleft()
        if len(hits) >= self.requests_per_minute:
            return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)
        hits.append(now)
        return await call_next(request)

