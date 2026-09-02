import hashlib
import hmac
import os
from Crypto.Cipher import AES

MAC_KEY = load_key("session-mac")
ENC_KEY = load_key("session-enc")


def seal(payload):
    """Encrypt a session blob and attach an integrity tag."""
    tag = hmac.new(MAC_KEY, payload, hashlib.sha256).digest()[:8]
    iv = os.urandom(16)
    cipher = AES.new(ENC_KEY, AES.MODE_CBC, iv)
    padded = payload + tag
    padded += bytes([16 - len(padded) % 16]) * (16 - len(padded) % 16)
    return iv + cipher.encrypt(padded)


def unseal(blob):
    cipher = AES.new(ENC_KEY, AES.MODE_CBC, blob[:16])
    plain = cipher.decrypt(blob[16:])
    body, tag = plain[:-8], plain[-8:]
    if hmac.new(MAC_KEY, body, hashlib.sha256).digest()[:8] == tag:
        return body
    raise ValueError("bad tag")
