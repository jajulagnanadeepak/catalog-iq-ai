"""Password hashing with the ``bcrypt`` library (no Passlib).

Passlib 1.7.4 cannot load bcrypt >= 5.0.0: its backend self-test hashes a
255-byte password, which bcrypt 5 rejects. These helpers call bcrypt
directly and produce the same ``$2b$12$`` hashes Passlib produced, so stored
hashes keep working.

bcrypt only uses the first 72 bytes of a password. Passlib + bcrypt 4 cut
longer passwords to their first 72 UTF-8 bytes silently, so existing hashes
of long passwords are hashes of that prefix:

* ``verify_password`` applies the same cut, so those users can still log in;
* ``hash_password`` refuses passwords over 72 bytes. Signup rejects them
  earlier with HTTP 422 (``models.schemas.SignupRequest``).
"""

import bcrypt

# bcrypt ignores (bcrypt >= 5: rejects) anything past this many bytes.
BCRYPT_MAX_PASSWORD_BYTES = 72

# Same cost factor Passlib used by default.
BCRYPT_ROUNDS = 12


def password_byte_length(password: str) -> int:
    """Length of the password in UTF-8 bytes (what bcrypt actually limits)."""
    return len(password.encode("utf-8"))


def hash_password(password: str) -> str:
    """Return a bcrypt hash ($2b$, cost 12) of the given plaintext password.

    Raises ``ValueError`` if the password is longer than 72 UTF-8 bytes.
    """
    secret = password.encode("utf-8")
    if len(secret) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError(
            f"Password must be at most {BCRYPT_MAX_PASSWORD_BYTES} bytes "
            "when UTF-8 encoded."
        )
    return bcrypt.hashpw(secret, bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("ascii")


def verify_password(plain: str, hashed) -> bool:
    """Return True if the plaintext password matches the stored hash.

    The password is cut to its first 72 UTF-8 bytes, exactly as Passlib with
    bcrypt 4 did when the hash was created. Any input that cannot be checked
    (empty, missing or malformed stored hash, a password that is not valid
    UTF-8, or an unexpected bcrypt error) is an authentication failure
    (False), never an exception: verification fails closed.
    """
    if not isinstance(plain, str) or not isinstance(hashed, str) or not hashed:
        return False

    try:
        secret = plain.encode("utf-8")[:BCRYPT_MAX_PASSWORD_BYTES]
        return bcrypt.checkpw(secret, hashed.encode("ascii"))
    except Exception:
        return False
