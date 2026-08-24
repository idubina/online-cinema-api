import pytest

from app.validators.accounts import (
    validate_email,
    validate_password_strength,
)


@pytest.mark.parametrize(
    ("password", "expected_error"),
    [
        (
            "Ab1!xyz",
            "Password must contain at least 8 characters.",
        ),
        (
            "password1!",
            "Password must contain at least one uppercase letter.",
        ),
        (
            "PASSWORD1!",
            "Password must contain at least one lower letter.",
        ),
        (
            "Password!",
            "Password must contain at least one digit.",
        ),
        (
            "Password1",
            "Password must contain at least one special character",
        ),
        (
            "Ab1!",
            "Password must contain at least 8 characters.",
        ),
    ],
)
def test_validate_password_strength_invalid_password(
    password: str,
    expected_error: str,
):
    with pytest.raises(ValueError, match=expected_error):
        validate_password_strength(password)


def test_validate_password_strength_valid_password():
    password = "Password1!"

    result = validate_password_strength(password)

    assert result == password


def test_validate_email_valid_email():
    email = "test@example.com"

    result = validate_email(email)

    assert result == email


def test_validate_email_normalizes_email():
    email = "test@EXAMPLE.COM"

    result = validate_email(email)

    assert result == "test@example.com"


@pytest.mark.parametrize(
    "email",
    [
        "invalid-email",
        "@example.com",
        "test@",
        "test example.com",
    ],
)
def test_validate_email_invalid_email(email: str):
    with pytest.raises(ValueError):
        validate_email(email)


def test_validate_email_strips_whitespace():
    result = validate_email("test@example.com")

    assert result == "test@example.com"
