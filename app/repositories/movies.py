from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.movies import (
    CountryModel,
    GenreModel,
    ActorModel,
    LanguageModel,
    MovieModel,
)

from app.schemas import movies as schemas


async def get_or_create_country_by_code(db: AsyncSession, country_code: str):
    country = await db.scalar(
        select(CountryModel).where(CountryModel.code == country_code)
    )
    if country is None:
        country = CountryModel(code=country_code)
        db.add(country)
        await db.flush()
    return country


async def get_or_create_genre(db: AsyncSession, genre_name: str):
    genre = await db.scalar(select(GenreModel).where(GenreModel.name == genre_name))
    if genre is None:
        genre = GenreModel(name=genre_name)
        db.add(genre)
        await db.flush()
    return genre


async def get_or_create_actor(db: AsyncSession, actor_name: str):
    actor = await db.scalar(select(ActorModel).where(ActorModel.name == actor_name))
    if actor is None:
        actor = ActorModel(name=actor_name)
        db.add(actor)
        await db.flush()
    return actor


async def get_or_create_language(db: AsyncSession, language_name: str):
    language = await db.scalar(
        select(LanguageModel).where(LanguageModel.name == language_name)
    )
    if language is None:
        language = LanguageModel(name=language_name)
        db.add(language)
        await db.flush()
    return language


async def create_movie(db: AsyncSession, movie_data: schemas.MovieCreateSchema):

    country = await get_or_create_country_by_code(
        db=db, country_code=movie_data.country
    )

    genres = [
        await get_or_create_genre(db, genre_name)
        for genre_name in dict.fromkeys(movie_data.genres)
    ]

    actors = [
        await get_or_create_actor(db, actor_name)
        for actor_name in dict.fromkeys(movie_data.actors)
    ]

    languages = [
        await get_or_create_language(db, language_name)
        for language_name in dict.fromkeys(movie_data.languages)
    ]

    movie_db = MovieModel(
        **movie_data.model_dump(exclude={"country", "genres", "actors", "languages"}),
        country=country,
        genres=genres,
        actors=actors,
        languages=languages,
    )

    db.add(movie_db)

    await db.commit()

    return movie_db


async def name_and_date_is_unique(
    db: AsyncSession,
    movie_name,
    movie_date,
) -> bool:
    existing_movie = await db.scalar(
        select(MovieModel).where(
            MovieModel.name == movie_name,
            MovieModel.date == movie_date,
        )
    )
    return existing_movie is None


async def get_movie_by_id(db: AsyncSession, movie_id: id):
    return await db.scalar(
        select(MovieModel)
        .options(
            selectinload(MovieModel.country),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages),
        )
        .where(MovieModel.id == movie_id)
    )


async def get_movie_items_count(db: AsyncSession):
    return await db.scalar(select(func.count()).select_from(MovieModel))


async def get_movie_list(db: AsyncSession, offset: int, per_page: int = 10):
    stmt = await db.scalars(
        select(MovieModel).order_by(MovieModel.id.desc()).offset(offset).limit(per_page)
    )
    return stmt.all()


async def update_movie(db: AsyncSession, movie: MovieModel, update_data):
    for field, value in update_data.items():
        setattr(movie, field, value)

    await db.commit()


async def delete_movie(db: AsyncSession, movie: MovieModel):
    await db.delete(movie)
    await db.commit()
