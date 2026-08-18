from app.core.security import hash_password, verify_password


def test_hash_password():
    plain_password = "Password1234!"
    hashed_password = hash_password(plain_password)
    assert plain_password != hashed_password
    assert isinstance(hashed_password, str)


def test_verify_correct_password():
    plain_password = "Password1234!"
    hashed_password = hash_password(plain_password)
    assert verify_password(plain_password, hashed_password) is True


def test_verify_incorrect_password():
    hashed_password = hash_password("Password1234!")
    assert verify_password("WrongPassword", hashed_password) is False
