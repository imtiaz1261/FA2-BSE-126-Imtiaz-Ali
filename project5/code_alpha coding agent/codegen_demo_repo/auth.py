import os
import hashlib


def hash_password(password, salt=None):
    salt = salt or os.urandom(16).hex()
    return hashlib.sha256((salt + password).encode()).hexdigest(), salt


def check_password(password, hashed):
    return hash_password(password) == hashed
