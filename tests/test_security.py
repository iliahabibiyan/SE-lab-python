from app.security import hash_password, verify_password


def test_hash_is_bcrypt_and_not_plain_text():
    hashed = hash_password("Str0ng-pass1")
    assert hashed.startswith("$2")
    assert "Str0ng-pass1" not in hashed


def test_same_password_gives_different_hashes():
    assert hash_password("Str0ng-pass1") != hash_password("Str0ng-pass1")  # random salt


def test_verify_password():
    hashed = hash_password("Str0ng-pass1")
    assert verify_password("Str0ng-pass1", hashed)
    assert not verify_password("wrong-pass", hashed)


def test_verify_password_with_missing_or_broken_hash():
    assert not verify_password("Str0ng-pass1", None)
    assert not verify_password("Str0ng-pass1", "")
    assert not verify_password("Str0ng-pass1", "not-a-bcrypt-hash")


def test_persian_password():
    hashed = hash_password("رمز-عبور-قوی-۱۲۳")
    assert verify_password("رمز-عبور-قوی-۱۲۳", hashed)