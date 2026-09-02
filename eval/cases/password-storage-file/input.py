import bcrypt
from cryptography.fernet import Fernet

VAULT = Fernet(load_key("password-vault"))


def store_password(user, password):
    """Hash for login, keep a recoverable copy for the support desk."""
    user.pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=6))
    user.pw_recoverable = VAULT.encrypt(password.encode())
    user.save()
