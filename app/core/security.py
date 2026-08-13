from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """
    Hash a plain-text password using the recommended password hasher.

    Args:
        password: Plain-text password.

    Returns:
        Hashed password.
    """
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """
    Verify a plain-text password against a stored password hash.

    Args:
        plain_password: Plain-text password provided by the user.
        hashed_password: Password hash stored in the database.

    Returns:
        True if the password matches, otherwise False.
    """
    return password_hash.verify(
        plain_password,
        hashed_password,
    )
