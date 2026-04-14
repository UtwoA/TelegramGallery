from urllib.parse import quote

from fastapi import Request
from starlette.responses import RedirectResponse



def is_admin(request: Request) -> bool:
    return bool(request.session.get("is_admin"))


def is_authenticated(request: Request) -> bool:
    return is_admin(request)


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def auth_guard(request: Request):
    if is_authenticated(request):
        return None
    target = quote(str(request.url.path))
    return RedirectResponse(url=f"/login?next={target}", status_code=303)


def admin_guard(request: Request):
    return auth_guard(request)
