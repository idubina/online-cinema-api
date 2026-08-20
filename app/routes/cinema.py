from fastapi import APIRouter, status

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
