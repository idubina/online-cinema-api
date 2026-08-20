from typing import Annotated

from fastapi import APIRouter, status, Depends

from app.dependencies import SessionDep, CurrentUserDep, S3StorageDep
from app.schemas import profiles as schemas
from app.services import profiles as profile_services

router = APIRouter()


@router.post(
    "/{user_id}/profile/",
    response_model=schemas.ProfileResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_profile(
    db: SessionDep,
    user_id: int,
    profile_data: Annotated[
        schemas.UserProfileCreateRequestSchema,
        Depends(schemas.UserProfileCreateRequestSchema.as_form),
    ],
    current_user: CurrentUserDep,
    storage: S3StorageDep,
):
    profile, avatar_url = await profile_services.create_profile(
        db=db,
        profile_data=profile_data,
        user_id=user_id,
        current_user_id=current_user.id,
        current_user_group=current_user.group.name,
        storage=storage,
    )
    profile_res = schemas.ProfileResponseSchema(
        id=profile.id,
        user_id=user_id,
        first_name=profile.first_name,
        last_name=profile.last_name,
        gender=profile.gender,
        date_of_birth=profile.date_of_birth,
        info=profile.info,
        avatar=avatar_url,
    )
    return profile_res


@router.get(
    "/{user_id}/profile/",
    response_model=schemas.ProfileResponseSchema,
)
async def get_profile(
    db: SessionDep,
    user_id: int,
    current_user: CurrentUserDep,
    storage: S3StorageDep,
):
    profile, avatar_url = await profile_services.get_profile(
        db=db,
        user_id=user_id,
        current_user_id=current_user.id,
        current_user_group=current_user.group.name,
        storage=storage,
    )

    return schemas.ProfileResponseSchema(
        id=profile.id,
        user_id=profile.user_id,
        first_name=profile.first_name,
        last_name=profile.last_name,
        gender=profile.gender,
        date_of_birth=profile.date_of_birth,
        info=profile.info,
        avatar=avatar_url,
    )
