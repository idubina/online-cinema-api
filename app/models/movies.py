import enum
from datetime import date as date_type
from decimal import Decimal

from sqlalchemy import (
    Column,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MovieStatusEnum(str, enum.Enum):
    RELEASED = "Released"
    POST_PRODUCTION = "Post Production"
    IN_PRODUCTION = "In Production"


movies_genres_table = Table(
    "movies_genres",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "genre_id",
        ForeignKey("genres.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


actors_movies_table = Table(
    "actors_movies",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "actor_id",
        ForeignKey("actors.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


movies_languages_table = Table(
    "movies_languages",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "language_id",
        ForeignKey("languages.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class GenreModel(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    movies: Mapped[list["MovieModel"]] = relationship(
        secondary=movies_genres_table,
        back_populates="genres",
    )

    def __repr__(self) -> str:
        return f"<Genre(name='{self.name}')>"


class ActorModel(Base):
    __tablename__ = "actors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    movies: Mapped[list["MovieModel"]] = relationship(
        secondary=actors_movies_table,
        back_populates="actors",
    )

    def __repr__(self) -> str:
        return f"<Actor(name='{self.name}')>"


class CountryModel(Base):
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(
        String(3),
        unique=True,
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    movies: Mapped[list["MovieModel"]] = relationship(
        back_populates="country",
    )

    def __repr__(self) -> str:
        return f"<Country(code='{self.code}', name='{self.name}')>"


class LanguageModel(Base):
    __tablename__ = "languages"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    movies: Mapped[list["MovieModel"]] = relationship(
        secondary=movies_languages_table,
        back_populates="languages",
    )

    def __repr__(self) -> str:
        return f"<Language(name='{self.name}')>"


class MovieModel(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    date: Mapped[date_type] = mapped_column(
        nullable=False,
    )
    score: Mapped[float] = mapped_column(
        nullable=False,
    )
    overview: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[MovieStatusEnum] = mapped_column(
        Enum(MovieStatusEnum),
        nullable=False,
    )
    budget: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
    )
    revenue: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
    )

    country_id: Mapped[int] = mapped_column(
        ForeignKey("countries.id"),
        nullable=False,
    )

    country: Mapped["CountryModel"] = relationship(
        back_populates="movies",
    )

    genres: Mapped[list["GenreModel"]] = relationship(
        secondary=movies_genres_table,
        back_populates="movies",
    )

    actors: Mapped[list["ActorModel"]] = relationship(
        secondary=actors_movies_table,
        back_populates="movies",
    )

    languages: Mapped[list["LanguageModel"]] = relationship(
        secondary=movies_languages_table,
        back_populates="movies",
    )

    __table_args__ = (
        UniqueConstraint(
            "name",
            "date",
            name="unique_movie_constraint",
        ),
    )

    @classmethod
    def default_order_by(cls):
        return [cls.id.desc()]

    def __repr__(self) -> str:
        return (
            f"<Movie("
            f"name='{self.name}', "
            f"release_date='{self.date}', "
            f"score={self.score}"
            f")>"
        )
