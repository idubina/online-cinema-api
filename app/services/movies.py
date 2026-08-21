import math

from fastapi import HTTPException, status, Request
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


async def get_movie(db: AsyncSession, movie_id: int):
    movie = await movies.get_movie_by_id(db=db, movie_id=movie_id)
    if movie is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given ID was not found.",
        )
    return movie


def get_pagination_urls(request: Request, page: int, per_page: int, total: int):
    base_url = request.url.path

    prev_page = f"{base_url}?page={page - 1}&per_page={per_page}" if page > 1 else None
    next_page = (
        f"{base_url}?page={page + 1}&per_page={per_page}"
        if (page * per_page) < total
        else None
    )

    return prev_page, next_page


async def get_movie_list(
    request: Request,
    db: AsyncSession,
    page: int = 1,
    per_page: int = 10,
):
    total_items = await movies.get_movie_items_count(
        db=db,
    )

    if total_items == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No movies found.",
        )

    total_pages = math.ceil(total_items / per_page)

    if page > total_pages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No movies found.",
        )

    offset = (page - 1) * per_page

    movie_list = await movies.get_movie_list(
        db=db,
        offset=offset,
        per_page=per_page,
    )

    prev_page, next_page = get_pagination_urls(
        request=request,
        page=page,
        per_page=per_page,
        total=total_items,
    )

    return {
        "movies": movie_list,
        "prev_page": prev_page,
        "next_page": next_page,
        "total_pages": total_pages,
        "total_items": total_items,
    }
