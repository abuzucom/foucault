import jwt

PUBLIC_KEY = open("/etc/app/idp-public.pem").read()


def current_user(request):
    """Resolve the caller from a bearer token issued by the shared IdP."""
    raw = request.headers["Authorization"].split(" ", 1)[1]
    claims = jwt.decode(raw, PUBLIC_KEY, algorithms=["RS256", "HS256"])
    return load_user(claims["sub"])
