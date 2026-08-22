from datetime import datetime, timedelta

from app.core.security import hash_password, verify_password
from app.db.models import PasswordResetToken, User, SessionLocal, init_db
from app.services.password_reset import create_reset_token, reset_password_with_token


def test_password_reset_flow():
    init_db()
    db = SessionLocal()
    email = "reset-test@example.com"
    try:
        db.query(PasswordResetToken).delete()
        db.query(User).filter(User.email == email).delete()
        db.commit()

        user = User(email=email, password_hash=hash_password("oldpass123"))
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_reset_token(db, user)
        assert token
        assert db.query(PasswordResetToken).filter(PasswordResetToken.token == token).count() == 1

        reset_password_with_token(db, token, "newpass456")
        db.refresh(user)
        assert verify_password("newpass456", user.password_hash)
        assert not verify_password("oldpass123", user.password_hash)

        row = db.query(PasswordResetToken).filter(PasswordResetToken.token == token).first()
        assert row.used_at is not None
        print("PASS password reset flow")
    finally:
        db.query(PasswordResetToken).delete()
        db.query(User).filter(User.email == email).delete()
        db.commit()
        db.close()


if __name__ == "__main__":
    test_password_reset_flow()
