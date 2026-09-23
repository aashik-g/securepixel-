"""Password-based AES-256-GCM encryption helpers for SecurePixel."""

import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

SALT_SIZE = 16
NONCE_SIZE = 12
KEY_SIZE = 32
PBKDF2_ITERATIONS = 600_000


def derive_key(password: str, salt: bytes) -> bytes:
    """Derive a 256-bit AES key from a password and per-message salt."""
    if not isinstance(password, str) or not password:
        raise ValueError("A password is required.")
    if len(salt) != SALT_SIZE:
        raise ValueError("Invalid salt.")

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt_message(message: str, password: str) -> tuple[bytes, bytes, bytes]:
    """Return salt, nonce, and AES-GCM ciphertext (including its tag)."""
    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    key = derive_key(password, salt)
    ciphertext = AESGCM(key).encrypt(nonce, message.encode("utf-8"), None)
    return salt, nonce, ciphertext


def decrypt_message(ciphertext: bytes, password: str, salt: bytes, nonce: bytes) -> str:
    """Authenticate and decrypt a ciphertext, raising on any tampering."""
    key = derive_key(password, salt)
    plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")
