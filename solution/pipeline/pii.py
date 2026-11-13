import base64
import hashlib
import hmac
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _secret(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(name + " must be set in the environment")
    return value.encode("utf-8")


def phone_hash(canonical_phone):
    return hmac.new(_secret("PII_HMAC_KEY"), canonical_phone.encode(), hashlib.sha256).hexdigest()


def _encryption_key():
    try:
        key = base64.b64decode(_secret("PII_ENC_KEY"), validate=True)
    except (ValueError, TypeError) as error:
        raise RuntimeError("PII_ENC_KEY must be base64 for 32 random bytes") from error
    if len(key) != 32:
        raise RuntimeError("PII_ENC_KEY must decode to 32 bytes")
    return key


def encrypt(value):
    nonce = os.urandom(12)
    return nonce + AESGCM(_encryption_key()).encrypt(nonce, value.encode(), None)


def decrypt(value):
    if value is None:
        return ""
    return AESGCM(_encryption_key()).decrypt(value[:12], value[12:], None).decode()
