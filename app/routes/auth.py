from fastapi import APIRouter, status
from ..schemas import auth as auth_schemas
from ..dependencies import SessionDep
from ..services import auth as auth_services

router = APIRouter()


@router.post(
    "/register/",
    response_model=auth_schemas.UserRegistrationResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    db: SessionDep, user_data: auth_schemas.UserRegistrationRequestSchema
):
    return await auth_services.create_user(db=db, user_data=user_data)


@router.post(
    "/activate/",
    response_model=auth_schemas.MessageResponseSchema,
)
async def activate_user(
    db: SessionDep, user_data: auth_schemas.UserActivationRequestSchema
):
    await auth_services.activate_user(db=db, user_data=user_data)
    message = auth_schemas.MessageResponseSchema(
        message="User account activated successfully."
    )
    return message
