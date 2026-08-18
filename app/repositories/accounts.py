from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.accounts import (
    UserModel,
    UserGroupModel,
    UserGroupEnum,
    ActivationTokenModel,
    PasswordResetTokenModel,
)


async def get_user_by_email(db: AsyncSession, email):
    return await db.scalar(select(UserModel).where(UserModel.email == email))


async def get_user_by_id(db: AsyncSession, id):
    return await db.scalar(select(UserModel).where(UserModel.id == id))


async def get_default_user_group(db: AsyncSession):
    return await db.scalar(
        select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
    )


async def get_activation_token_by_token(db: AsyncSession, token):
    return await db.scalar(
        select(ActivationTokenModel).where(ActivationTokenModel.token == token)
    )


async def create_user(db: AsyncSession, **user_data):
    try:
        user_group = await get_default_user_group(db=db)
        user = UserModel(
            email=user_data.get("email"), group=user_group, is_active=False
        )
        user.password = user_data.get("password")
        activation_token = ActivationTokenModel()
        user.activation_token = activation_token

        db.add(activation_token)
        db.add(user)

        await db.commit()
        await db.refresh(user)

        return user

    except Exception as error:
        await db.rollback()
        raise error


async def activate_user(db: AsyncSession, user: UserModel, token: ActivationTokenModel):
    user.is_active = True
    db.add(user)
    await db.delete(token)
    await db.commit()


async def create_reset_token(db: AsyncSession, user_db: UserModel):
    await db.execute(
        delete(PasswordResetTokenModel).where(
            PasswordResetTokenModel.user_id == user_db.id
        )
    )

    new_reset_token = PasswordResetTokenModel(user_id=user_db.id)
    db.add(new_reset_token)
    await db.commit()
