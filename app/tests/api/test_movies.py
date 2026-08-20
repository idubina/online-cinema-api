from datetime import date, timedelta

import pytest


from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounts import UserModel, UserGroupModel, UserGroupEnum
from app.models.movies import MovieModel

pytestmark = pytest.mark.anyio

CINEMA_URL = "/api/cinema"


async def test_create_movie_success(
    client: AsyncClient, db_session: AsyncSession, authenticated_user
):
    user, access_token = authenticated_user
    current_user = await db_session.scalar(
        select(UserModel).where(UserModel.id == user["id"])
    )

    current_user.group = await db_session.scalar(
        select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.MODERATOR)
    )
    db_session.add(current_user)
    await db_session.commit()

    movie_payload_1 = {
        "name": "Test",
        "date": "2020-08-20",
        "score": 89,
        "overview": "Tested",
        "status": "Released",
        "budget": "12345654",
        "revenue": "76543245",
    }

    movie_payload_2 = {
        "country": "USA",
        "genres": ["Test Genre"],
        "actors": ["Test Actor 1", "Test Actor 2"],
        "languages": ["Test Language"],
    }

    movie_payload_full = movie_payload_1 | movie_payload_2

    response = await client.post(
        f"{CINEMA_URL}/movies/",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json=movie_payload_full,
    )

    assert response.status_code == 201

    data = response.json()

    movie = await db_session.scalar(
        select(MovieModel).where(MovieModel.id == data["id"])
    )

    assert movie is not None

    for key, value in movie_payload_1.items():
        assert data[key] == value

    assert movie_payload_full["country"] == data["country"]["code"]

    assert {genre["name"] for genre in data["genres"]} == set(
        movie_payload_full["genres"]
    )

    assert {actor["name"] for actor in data["actors"]} == set(
        movie_payload_full["actors"]
    )

    assert {language["name"] for language in data["languages"]} == set(
        movie_payload_full["languages"]
    )


async def test_default_user_create_movie_forbidden(
    client: AsyncClient, db_session: AsyncSession, authenticated_user
):
    access_token = authenticated_user[1]

    response = await client.post(
        f"{CINEMA_URL}/movies/",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 403

    detail = response.json()["detail"]
    assert detail == "You do not have permission to perform this action."


async def test_unauthenticated_user_create_movie_not_allowed(
    client: AsyncClient, db_session: AsyncSession
):

    response = await client.post(
        f"{CINEMA_URL}/movies/",
    )

    assert response.status_code == 401

    detail = response.json()["detail"]
    assert detail == "Not authenticated"


async def test_create_movie_with_date_more_than_one_year_in_the_future_error(
    client: AsyncClient, db_session: AsyncSession, authenticated_user
):
    user, access_token = authenticated_user
    current_user = await db_session.scalar(
        select(UserModel).where(UserModel.id == user["id"])
    )

    current_user.group = await db_session.scalar(
        select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.MODERATOR)
    )
    db_session.add(current_user)
    await db_session.commit()

    incorrect_date = str(date.today() + timedelta(days=366))

    movie_payload_1 = {
        "name": "Test",
        "date": incorrect_date,
        "score": 89,
        "overview": "Tested",
        "status": "Released",
        "budget": "12345654",
        "revenue": "76543245",
    }

    movie_payload_2 = {
        "country": "USA",
        "genres": ["Test Genre"],
        "actors": ["Test Actor 1", "Test Actor 2"],
        "languages": ["Test Language"],
    }

    movie_payload_full = movie_payload_1 | movie_payload_2

    response = await client.post(
        f"{CINEMA_URL}/movies/",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json=movie_payload_full,
    )

    assert response.status_code == 422

    detail = response.json()["detail"]
    assert (
        "Release date cannot be more than one year in the future." in detail[0]["msg"]
    )


async def test_create_movie_with_same_date_and_name_error(
    client: AsyncClient, db_session: AsyncSession, authenticated_user
):
    user, access_token = authenticated_user
    current_user = await db_session.scalar(
        select(UserModel).where(UserModel.id == user["id"])
    )

    current_user.group = await db_session.scalar(
        select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.MODERATOR)
    )
    db_session.add(current_user)
    await db_session.commit()

    movie_payload_1 = {
        "name": "Test",
        "date": "2020-08-20",
        "score": 89,
        "overview": "Tested",
        "status": "Released",
        "budget": "12345654",
        "revenue": "76543245",
    }

    movie_payload_2 = {
        "country": "USA",
        "genres": ["Test Genre"],
        "actors": ["Test Actor 1", "Test Actor 2"],
        "languages": ["Test Language"],
    }

    movie_payload_full = movie_payload_1 | movie_payload_2

    response_1 = await client.post(
        f"{CINEMA_URL}/movies/",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json=movie_payload_full,
    )

    assert response_1.status_code == 201

    response_2 = await client.post(
        f"{CINEMA_URL}/movies/",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json=movie_payload_full,
    )

    assert response_2.status_code == 409

    detail = response_2.json()["detail"]
    movie_name = movie_payload_full["name"]
    movie_date = movie_payload_full["date"]
    assert (
        detail
        == f"A movie with the name '{movie_name}' and release date '{movie_date}' already exists."
    )
