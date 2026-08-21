from typing import Annotated

from fastapi import APIRouter, status, Request, Query
from watchfiles import awatch

from app.dependencies import SessionDep, ModeratorDep
from app.schemas import movies as schemas
from app.services import movies as movie_services

router = APIRouter()


@router.post(
    "/movies/",
    response_model=schemas.MovieDetailSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_movie(
    db: SessionDep, movie_data: schemas.MovieCreateSchema, current_use: ModeratorDep
):
    return await movie_services.create_movie(db=db, movie_data=movie_data)


@router.get(
    "/movies/{movie_id}/",
    response_model=schemas.MovieDetailSchema,
)
async def read_movie(db: SessionDep, movie_id: int):
    return await movie_services.get_movie(db=db, movie_id=movie_id)


@router.get("/movies/", response_model=schemas.MovieListResponseSchema)
async def read_all_movies(
    request: Request,
    db: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=20)] = 10,
):
    return await movie_services.get_movie_list(
        request=request, db=db, page=page, per_page=per_page
    )
