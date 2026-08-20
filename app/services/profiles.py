from pathlib import Path
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.accounts import UserGroupEnum
from app.schemas import profiles as schemas
from app.repositories import profiles, accounts

from app.storages import S3StorageInterface


async def create_profile(
    db: AsyncSession,
    profile_data: schemas.UserProfileCreateRequestSchema,
    user_id: int,
    current_user_id: int,
    current_user_group: UserGroupEnum,
    storage: S3StorageInterface,
):

    if not await accounts.user_active_and_exists(db=db, user_id=user_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or not active.",
        )

    if current_user_id != user_id and current_user_group != UserGroupEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to create this profile.",
        )

    profile = await profiles.get_profile_by_user_id(db=db, user_id=user_id)
    if profile is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a profile.",
        )

    avatar = profile_data.avatar

    extension = Path(avatar.filename or "").suffix.lower()

    if not extension:
        extension = ".jpg"

    file_name = f"{user_id}/{uuid4()}{extension}"

    file_data = await avatar.read()
    try:
        await storage.upload_file(
            file_name=file_name,
            file_data=file_data,
            content_type=avatar.content_type or "application/octet-stream",
        )

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload avatar. Please try again later.",
        ) from error

    try:
        profile = await profiles.create_profile(
            db=db,
            user_id=user_id,
            first_name=profile_data.first_name,
            last_name=profile_data.last_name,
            gender=profile_data.gender,
            date_of_birth=profile_data.date_of_birth,
            info=profile_data.info,
            avatar=file_name,
        )

    except Exception as error:
        try:
            await storage.delete_file(file_name)
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user profile.",
        ) from error

    avatar_url = await storage.get_file_url(profile.avatar)

    return profile, avatar_url
