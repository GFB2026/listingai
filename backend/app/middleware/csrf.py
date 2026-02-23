"""Double-submit cookie CSRF protection for state-changing requests.

How it works:
1. On any response, if no csrf_token cookie exists, set one with a random value.
2. On POST/PUT/PATCH/DELETE requests using cookie auth, require X-CSRF-Token header
   matching the csrf_token cookie value.
3. Bearer-token-only requests (no cookies) skip CSRF — they're not vulnerable.
4. Whitelisted paths (webhooks, health) skip CSRF.
"""
import secrets

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"

# Paths that skip CSRF (webhooks need raw POST without frontend involvement)
CSRF_EXEMPT_PATHS = {
    "/api/v1/webhooks/stripe",
    "/health",
    "/health/live",
    "/health/ready",
    "/metrics",
}

STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Only enforce on state-changing methods
        if request.method not in STATE_CHANGING_METHODS:
            response = await call_next(request)
            self._ensure_csrf_cookie(request, response)
            return response

        # Skip exempt paths
        if request.url.path in CSRF_EXEMPT_PATHS:
            return await call_next(request)

        # Only enforce if request uses cookie auth (has access_token cookie)
        # Bearer-only requests are not vulnerable to CSRF
        if "access_token" not in request.cookies:
            return await call_next(request)

        # Validate CSRF token
        cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
        header_token = request.headers.get(CSRF_HEADER_NAME)

        if not cookie_token or not header_token or cookie_token != header_token:
            return JSONResponse(
                status_code=403,
                content={"error": "csrf_error", "detail": "CSRF token missing or invalid"},
            )

        response = await call_next(request)
        self._ensure_csrf_cookie(request, response)
        return response

    @staticmethod
    def _ensure_csrf_cookie(request: Request, response: Response) -> None:
        """Set CSRF cookie if not already present."""
        if CSRF_COOKIE_NAME not in request.cookies:
            settings = get_settings()
            response.set_cookie(
                key=CSRF_COOKIE_NAME,
                value=secrets.token_urlsafe(32),
                httponly=False,  # Must be readable by JavaScript
                secure=settings.app_env == "production",
                samesite="lax",
                max_age=86400,  # 24 hours
                path="/",
            )
