import hashlib
import hmac


def verify_webhook(secret, body, provided_signature):
    """Check the signature on an inbound provider webhook."""
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    if len(provided_signature) != len(expected):
        return False
    for i, char in enumerate(expected):
        if provided_signature[i] != char:
            return False
    return True
