from fastapi import APIRouter, status, BackgroundTasks

from app.core.config import settings
from app.schemas import auth as auth_schemas
from app.dependencies import SessionDep, EmailSenderDep, CurrentUserDep
from app.services import auth as auth_services

router = APIRouter()


@router.post(
    "/register/",
    response_model=auth_schemas.UserRegistrationResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Register user",
)
async def register_user(
    db: SessionDep,
    user_data: auth_schemas.UserRegistrationRequestSchema,
    background_tasks: BackgroundTasks,
    email_sender: EmailSenderDep,
):

    user, activation_token = await auth_services.create_user(db=db, user_data=user_data)
    activation_link = f"{settings.FRONTEND_URL}/activate" f"?token={activation_token}"

    background_tasks.add_task(
        email_sender.send_activation_email,
        user.email,
        activation_link,
    )
    return user


@router.post(
    "/activate/",
    response_model=auth_schemas.MessageResponseSchema,
    summary="Activate account",
)
async def activate_user(
    db: SessionDep,
    user_data: auth_schemas.UserActivationRequestSchema,
    background_tasks: BackgroundTasks,
    email_sender: EmailSenderDep,
):
    await auth_services.activate_user(db=db, user_data=user_data)

    background_tasks.add_task(
        email_sender.send_activation_complete_email,
        user_data.email,
        f"{settings.FRONTEND_URL}/login",
    )
    message = auth_schemas.MessageResponseSchema(
        message="User account activated successfully."
    )
    return message


@router.post(
    "/activate/resend/",
    response_model=auth_schemas.MessageResponseSchema,
    summary="Resend account activation",
)
async def resend_activation(
    db: SessionDep,
    user_data: auth_schemas.UserActivationResendRequestSchema,
    background_tasks: BackgroundTasks,
    email_sender: EmailSenderDep,
):
    result = await auth_services.resend_activation_token(
        db=db,
        user_data=user_data,
    )

    if result is not None:
        user, activation_token = result

        activation_link = (
            f"{settings.FRONTEND_URL}/activate" f"?token={activation_token}"
        )

        background_tasks.add_task(
            email_sender.send_activation_email,
            user.email,
            activation_link,
        )

    return auth_schemas.MessageResponseSchema(
        message=(
            "If the account exists and is not activated, "
            "an activation email will be sent."
        )
    )


@router.post(
    "/password-reset/request/",
    response_model=auth_schemas.MessageResponseSchema,
    summary="Request password reset",
)
async def request_password_reset_token(
    db: SessionDep,
    user_data: auth_schemas.PasswordResetRequestSchema,
    background_tasks: BackgroundTasks,
    email_sender: EmailSenderDep,
):
    reset_token = await auth_services.request_reset_token(db=db, user_data=user_data)

    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

    background_tasks.add_task(
        email_sender.send_password_reset_email,
        user_data.email,
        reset_link,
    )

    message = auth_schemas.MessageResponseSchema(
        message="If you are registered, you will receive an email with instructions."
    )
    return message


@router.post(
    "/password-reset/complete/",
    response_model=auth_schemas.MessageResponseSchema,
    summary="Reset password",
)
async def reset_password(
    db: SessionDep,
    user_data: auth_schemas.PasswordResetCompleteRequestSchema,
    background_tasks: BackgroundTasks,
    email_sender: EmailSenderDep,
):
    await auth_services.password_reset_complete(db=db, user_data=user_data)
    background_tasks.add_task(
        email_sender.send_password_reset_complete_email,
        user_data.email,
        f"{settings.FRONTEND_URL}/login",
    )
    message = auth_schemas.MessageResponseSchema(message="Password reset successfully.")
    return message


@router.post(
    "/login/", response_model=auth_schemas.UserLoginResponseSchema, summary="Login user"
)
async def login(db: SessionDep, user_data: auth_schemas.UserLoginRequestSchema):
    login_data = await auth_services.login_user(db=db, user_data=user_data)
    return auth_schemas.UserLoginResponseSchema(**login_data)


@router.post(
    "/refresh/",
    response_model=auth_schemas.TokenRefreshResponseSchema,
    summary="Refresh access token",
)
async def refresh_access_token(
    db: SessionDep, token_data: auth_schemas.TokenRefreshRequestSchema
):
    access_token = await auth_services.access_token_refresh(
        db=db, token_data=token_data
    )
    return auth_schemas.TokenRefreshResponseSchema(access_token=access_token)


@router.get(
    "/me/", response_model=auth_schemas.UserReadSchema, summary="Get current user"
)
async def get_me(
    current_user: CurrentUserDep,
):
    return current_user
