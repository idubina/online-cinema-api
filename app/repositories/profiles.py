from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.accounts import (
    UserProfileModel,
    GenderEnum,
)
from app.models.movies import MovieModel


async def get_profile_by_user_id(db: AsyncSession, user_id):
    return await db.scalar(
        select(UserProfileModel)
        .options(selectinload(UserProfileModel.favorite_movies))
        .where(UserProfileModel.user_id == user_id)
    )


async def create_profile(
    db: AsyncSession,
    user_id: int,
    first_name: str,
    last_name: str,
    gender: GenderEnum,
    date_of_birth: date,
    info: str,
    avatar: str,
):
    try:
        profile = UserProfileModel(
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            date_of_birth=date_of_birth,
            info=info,
            avatar=avatar,
        )

        db.add(profile)

        await db.commit()
        await db.refresh(profile)

        return profile

    except Exception:
        await db.rollback()
        raise


async def add_movie_to_favorites(
    db: AsyncSession,
    profile: UserProfileModel,
    movie: MovieModel,
):
    profile.favorite_movies.append(movie)
    await db.commit()


async def remove_movie_from_favorites(
    db: AsyncSession,
    profile: UserProfileModel,
    movie: MovieModel,
):
    profile.favorite_movies.remove(movie)
    await db.commit()
