from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User, get_db
from app.schemas.meeting import (
    ForgotPasswordRequest,
    GoogleLoginRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from app.services.google_auth import verify_google_access_token, verify_google_id_token
from app.services.password_reset import request_password_reset, reset_password_with_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    return UserResponse(id=user.id, email=user.email, full_name=user.full_name)


@router.post("/register", response_model=TokenResponse)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No account found. Please sign up first.",
        )
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account uses Google sign-in. Please continue with Google.",
        )
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/google", response_model=TokenResponse)
def google_login(data: GoogleLoginRequest, db: Session = Depends(get_db)):
    """Google sign-in — website and extension use separate OAuth clients (platform field)."""
    try:
        if data.id_token:
            payload = verify_google_id_token(data.id_token, platform=data.platform)
        else:
            payload = verify_google_access_token(data.access_token or "", platform=data.platform)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid Google token") from exc

    email = payload["email"]
    google_id = payload["sub"]
    name = payload.get("name")

    user = db.query(User).filter((User.google_id == google_id) | (User.email == email)).first()
    if not user:
        user = User(email=email, google_id=google_id, full_name=name)
        db.add(user)
    else:
        user.google_id = google_id
        if name and not user.full_name:
            user.full_name = name
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/logout")
def logout():
    return {"message": "Logout on client by deleting JWT."}


@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    from app.core.config import settings as cfg

    generic_msg = (
        "If an account exists for this email with a password, "
        "reset instructions have been sent."
    )
    if not cfg.emailjs_configured():
        raise HTTPException(
            status_code=503,
            detail="Password reset email is not configured on the server. Contact support.",
        )
    try:
        request_password_reset(db, data.email.strip().lower())
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"message": generic_msg}


@router.post("/reset-password", response_model=TokenResponse)
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        user = reset_password_with_token(db, data.token.strip(), data.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TokenResponse(access_token=create_access_token(user.id))
