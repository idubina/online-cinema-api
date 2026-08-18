from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.schemas import auth as schemas
from app.repositories import accounts
from app.core.security import JWTManager

import jwt


async def create_user(
    db: AsyncSession, user_data: schemas.UserRegistrationRequestSchema
):
    user_db = await accounts.get_user_by_email(db=db, email=user_data.email)

    if user_db is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with this email {user_data.email} already exists.",
        )
    try:
        user_db = await accounts.create_user(db=db, **user_data.model_dump())
        return user_db
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during user creation.",
        )


async def activate_user(
    db: AsyncSession, user_data: schemas.UserActivationRequestSchema
):
    token_db = await accounts.get_activation_token_by_token(
        db=db, token=user_data.token
    )
    if token_db is None or token_db.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired activation token.",
        )

    user_db = await accounts.get_user_by_id(db=db, id=token_db.user_id)

    if user_db.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is already active.",
        )
    if user_db.email != user_data.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired activation token.",
        )
    await accounts.activate_user(db=db, user=user_db, token=token_db)


async def request_reset_token(
    db: AsyncSession, user_data: schemas.PasswordResetRequestSchema
):

    user_db = await accounts.get_user_by_email(db=db, email=user_data.email)

    if user_db is None or not user_db.is_active:
        return

    await accounts.create_reset_token(db=db, user_db=user_db)


async def password_reset_complete(
    db: AsyncSession, user_data: schemas.PasswordResetCompleteRequestSchema
):
    user_db = await accounts.get_user_by_email(db=db, email=user_data.email)

    if user_db is None or not user_db.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or token."
        )

    token_db = await accounts.get_reset_token_by_user_id(db=db, user_id=user_db.id)

    if token_db is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or token."
        )

    if token_db.token != user_data.token or token_db.expires_at < datetime.now(
        timezone.utc
    ):
        await accounts.delete_item(db=db, item=token_db)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or token."
        )

    try:
        await accounts.reset_password(
            db=db, user=user_db, token=token_db, password=user_data.password
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resetting the password.",
        )


async def login_user(db: AsyncSession, user_data: schemas.UserLoginRequestSchema):
    user_db = await accounts.get_user_by_email(db=db, email=user_data.email)

    if user_db is None or not user_db.verify_password(raw_password=user_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user_db.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not activated.",
        )

    try:
        access_token = JWTManager.create_access_token(user_id=user_db.id)
        refresh_token = JWTManager.create_refresh_token(user_id=user_db.id)
        token_type = "bearer"
        await accounts.save_refresh_token(
            db=db, user_id=user_db.id, refresh_token=refresh_token
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request.",
        )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": token_type,
    }


async def access_token_refresh(
    db: AsyncSession,
    token_data: schemas.TokenRefreshRequestSchema,
):
    refresh_token = token_data.refresh_token

    try:
        payload = JWTManager.decode_refresh_token(token=refresh_token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token has expired.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid refresh token.",
        )

    token_db = await accounts.get_refresh_token_by_token(
        db=db,
        token=refresh_token,
    )
    if token_db is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found.",
        )

    user_db = await accounts.get_user_by_id(
        db=db,
        id=int(payload["sub"]),
    )
    if user_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return JWTManager.create_access_token(user_id=user_db.id)
