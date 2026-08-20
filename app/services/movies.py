from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import movies
from app.schemas import movies as schemas


async def movie_data_validation(
    db: AsyncSession,
    movie_data: schemas.MovieCreateSchema,
) -> None:
    if not await movies.name_and_date_is_unique(
        db=db,
        movie_data=movie_data,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"A movie with the name '{movie_data.name}' "
                f"and release date '{movie_data.date}' already exists."
            ),
        )


async def create_movie(
    db: AsyncSession,
    movie_data: schemas.MovieCreateSchema,
):
    await movie_data_validation(
        db=db,
        movie_data=movie_data,
    )

    return await movies.create_movie(
        db=db,
        movie_data=movie_data,
    )
