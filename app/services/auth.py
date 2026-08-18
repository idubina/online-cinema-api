from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.schemas import auth as schemas
from app.repositories import accounts


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
