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
