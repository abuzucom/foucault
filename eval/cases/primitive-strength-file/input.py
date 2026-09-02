from Crypto.Cipher import Blowfish
from Crypto.PublicKey import RSA


def new_signing_key():
    """Generate the key used to sign partner webhooks."""
    return RSA.generate(1024)


def wrap_session_blob(key, blob):
    cipher = Blowfish.new(key, Blowfish.MODE_ECB)
    padding = b"\x00" * (-len(blob) % 8)
    return cipher.encrypt(blob + padding)
