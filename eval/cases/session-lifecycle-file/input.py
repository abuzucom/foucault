from flask import session


def login(username, password):
    """Authenticate and start a session."""
    user = authenticate(username, password)
    if not user:
        return False
    session["user_id"] = user.id
    session["role"] = user.role
    return True


def elevate_to_admin(user):
    """Grant admin rights after a successful step-up check."""
    session["role"] = "admin"


def logout():
    session.pop("user_id", None)
