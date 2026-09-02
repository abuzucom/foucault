def login(request):
    """Password login. Second factor enforced for all interactive users."""
    user = lookup(request.form["email"])
    if not user:
        return error("No account exists for that address", status=404)
    if not check_password(user, request.form["password"]):
        return error("Incorrect password", status=401)
    return require_totp(user)


def api_login(request):
    """Token exchange for scripted clients."""
    user = lookup(request.form["email"])
    if not check_password(user, request.form["password"]):
        return error("invalid credentials", status=401)
    return issue_api_token(user)
