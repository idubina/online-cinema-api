import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.models.movies import MovieStatusEnum


class MovieCreateSchema(BaseModel):
    name: str = Field(max_length=255)
    date: datetime.date
    score: float = Field(ge=0, le=100)
    overview: str
    status: MovieStatusEnum
    budget: Decimal = Field(ge=0)
    revenue: Decimal = Field(ge=0)
    country: str
    genres: list[str]
    actors: list[str]
    languages: list[str]

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: datetime.date) -> datetime.date:
        if value > datetime.date.today() + datetime.timedelta(days=365):
            raise ValueError("Release date cannot be more than one year in the future.")

        return value


class IdNameDetailBase(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


class GenreSchema(IdNameDetailBase):
    pass


class ActorSchema(IdNameDetailBase):
    pass


class LanguageSchema(IdNameDetailBase):
    pass


class CountrySchema(BaseModel):
    id: int
    code: str
    name: str | None
    model_config = ConfigDict(from_attributes=True)


class MovieDetailSchema(BaseModel):
    id: int
    name: str
    date: datetime.date
    score: float
    overview: str
    status: MovieStatusEnum
    budget: Decimal
    revenue: Decimal
    country: CountrySchema
    genres: list[GenreSchema]
    actors: list[ActorSchema]
    languages: list[LanguageSchema]
    model_config = ConfigDict(from_attributes=True)


class MovieListDetailSchema(BaseModel):
    id: int
    name: str
    date: datetime.date
    score: float
    overview: str

    model_config = ConfigDict(from_attributes=True)


class MovieListResponseSchema(BaseModel):
    movies: list[MovieListDetailSchema]
    prev_page: str | None = None
    next_page: str | None = None
    total_pages: int
    total_items: int


class MovieUpdateSchema(BaseModel):

    name: str | None = Field(default=None, max_length=255)
    date: datetime.date | None = None
    score: float | None = Field(default=None, ge=0, le=100)
    overview: str | None = None
    status: MovieStatusEnum | None = None
    budget: Decimal | None = Field(default=None, ge=0)
    revenue: Decimal | None = Field(default=None, ge=0)

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: datetime.date | None) -> datetime.date | None:
        if value and value > datetime.date.today() + datetime.timedelta(days=365):
            raise ValueError("Release date cannot be more than one year in the future.")

        return value


class MessageResponseSchema(BaseModel):
    message: str
