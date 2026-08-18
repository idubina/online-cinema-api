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


@router.post(
    "/password-reset/request/",
    response_model=auth_schemas.MessageResponseSchema,
)
async def request_password_reset_token(
    db: SessionDep, user_data: auth_schemas.PasswordResetRequestSchema
):
    await auth_services.request_reset_token(db=db, user_data=user_data)
    message = auth_schemas.MessageResponseSchema(
        message="If you are registered, you will receive an email with instructions."
    )
    return message


@router.post(
    "/password-reset/complete/",
    response_model=auth_schemas.MessageResponseSchema,
)
async def reset_password(
    db: SessionDep, user_data: auth_schemas.PasswordResetCompleteRequestSchema
):
    await auth_services.password_reset_complete(db=db, user_data=user_data)
    message = auth_schemas.MessageResponseSchema(message="Password reset successfully.")
    return message
