from typing import Annotated

from fastapi import APIRouter, status, Request, Query

from app.dependencies import SessionDep, ModeratorDep, CurrentUserDep
from app.schemas import movies as schemas
from app.services import movies as movie_services

router = APIRouter()


@router.post(
    "/movies/",
    response_model=schemas.MovieDetailSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a movie",
    responses={
        401: {"description": "Access token is invalid, or has expired."},
        403: {"description": "You do not have permission to perform this action."},
        404: {"description": "User not found."},
        409: {
            "description": "A movie with current name and release date already exists."
        },
    },
)
async def create_movie(
    db: SessionDep, movie_data: schemas.MovieCreateSchema, current_user: ModeratorDep
):
    return await movie_services.create_movie(db=db, movie_data=movie_data)


@router.get(
    "/movies/{movie_id}/",
    response_model=schemas.MovieDetailSchema,
    summary="Get movie details",
    responses={
        404: {"description": "Movie with the given ID was not found."},
    },
)
async def read_movie(db: SessionDep, movie_id: int):
    return await movie_services.get_movie(db=db, movie_id=movie_id)


@router.get(
    "/movies/",
    response_model=schemas.MovieListResponseSchema,
    summary="Get movie list",
    responses={
        404: {"description": "No movies found."},
    },
)
async def read_all_movies(
    request: Request,
    db: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=20)] = 10,
):
    return await movie_services.get_movie_list(
        request=request, db=db, page=page, per_page=per_page
    )


@router.patch(
    "/movies/{movie_id}/",
    response_model=schemas.MessageResponseSchema,
    summary="Update a movie",
    responses={
        400: {"description": "No fields were provided for update."},
        401: {"description": "Access token is invalid, or has expired."},
        403: {"description": "You do not have permission to perform this action."},
        404: {
            "description": "User not found, or movie with the given ID was not found."
        },
        409: {
            "description": "A movie with current name and release date already exists."
        },
    },
)
async def update_movie(
    db: SessionDep,
    movie_id: int,
    movie_data: schemas.MovieUpdateSchema,
    current_user: ModeratorDep,
):
    await movie_services.update_movie(db=db, movie_id=movie_id, movie_data=movie_data)
    return schemas.MessageResponseSchema(message="Movie updated successfully.")


@router.delete(
    "/movies/{movie_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a movie",
    responses={
        401: {"description": "Access token is invalid, or has expired."},
        403: {"description": "You do not have permission to perform this action."},
        404: {
            "description": "User not found, or movie with the given ID was not found."
        },
    },
)
async def delete_movie(
    db: SessionDep,
    movie_id: int,
    current_user: ModeratorDep,
):
    await movie_services.delete_movie(
        db=db,
        movie_id=movie_id,
    )


@router.put(
    "/movies/{movie_id}/favorite/",
    response_model=schemas.MessageResponseSchema,
    summary="Add movie to favorites",
    responses={
        401: {"description": "Access token is invalid or has expired."},
        404: {
            "description": "User not found, or user profile not found, "
            "or movie with the given ID was not found."
        },
    },
)
async def add_movie_to_favorites(
    db: SessionDep,
    movie_id: int,
    current_user: CurrentUserDep,
):
    await movie_services.add_movie_to_favorites(
        db=db,
        user_id=current_user.id,
        movie_id=movie_id,
    )

    return schemas.MessageResponseSchema(
        message="Movie added to favorites successfully."
    )


@router.delete(
    "/movies/{movie_id}/favorite/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove movie from favorites",
    responses={
        401: {"description": "Access token is invalid or has expired."},
        404: {
            "description": "User not found, or user profile not found, "
            "or movie with the given ID was not found, "
            "or movie is not in favorites."
        },
    },
)
async def remove_movie_from_favorites(
    db: SessionDep,
    movie_id: int,
    current_user: CurrentUserDep,
):
    await movie_services.remove_movie_from_favorites(
        db=db,
        user_id=current_user.id,
        movie_id=movie_id,
    )
