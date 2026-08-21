import math
from datetime import date, timedelta
from decimal import Decimal

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


async def test_read_movie_success(
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

    create_response = await client.post(
        f"{CINEMA_URL}/movies/",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json=movie_payload_full,
    )

    assert create_response.status_code == 201

    create_response_data = create_response.json()

    read_response = await client.get(
        f"{CINEMA_URL}/movies/{create_response_data['id']}/"
    )

    assert read_response.status_code == 200

    read_response_data = read_response.json()
    create_response_data["budget"] = Decimal(create_response_data["budget"])
    create_response_data["revenue"] = Decimal(create_response_data["revenue"])
    read_response_data["budget"] = Decimal(read_response_data["budget"])
    read_response_data["revenue"] = Decimal(read_response_data["revenue"])
    assert read_response_data == create_response_data


async def test_read_movie_not_found_error(
    client: AsyncClient, db_session: AsyncSession
):

    read_response = await client.get(f"{CINEMA_URL}/movies/1/")

    assert read_response.status_code == 404

    detail = read_response.json()["detail"]

    assert detail == "Movie with the given ID was not found."


async def test_read_all_movie_success(
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
    total_items = 14

    for i in range(1, total_items + 1):
        movie_payload = movie_payload_full | {
            "name": f"Test {i}",
        }

        response = await client.post(
            f"{CINEMA_URL}/movies/",
            headers={
                "Authorization": f"Bearer {access_token}",
            },
            json=movie_payload,
        )

        assert response.status_code == 201

    per_page = 10
    page = 1
    total_pages = math.ceil(total_items / per_page)

    response = await client.get(f"{CINEMA_URL}/movies/?page={page}&per_page={per_page}")

    assert response.status_code == 200

    details = response.json()

    assert len(details["movies"]) == per_page
    assert details["total_items"] == total_items
    assert details["total_pages"] == total_pages
    assert details["prev_page"] is None

    next_page_number = page + 1

    assert (
        details["next_page"]
        == f"{CINEMA_URL}/movies/?page={next_page_number}&per_page={per_page}"
    )

    response = await client.get(details["next_page"])

    assert response.status_code == 200

    details = response.json()

    assert len(details["movies"]) == total_items - per_page
    assert details["total_items"] == total_items
    assert details["total_pages"] == total_pages
    assert details["next_page"] is None

    assert (
        details["prev_page"] == f"{CINEMA_URL}/movies/?page={page}&per_page={per_page}"
    )


async def test_get_movie_list_empty(client: AsyncClient):
    response = await client.get(f"{CINEMA_URL}/movies/")

    assert response.status_code == 404
    assert response.json()["detail"] == "No movies found."


async def test_get_movie_list_page_not_found(
    client: AsyncClient,
    db_session: AsyncSession,
    authenticated_user,
):
    user, access_token = authenticated_user

    current_user = await db_session.scalar(
        select(UserModel).where(UserModel.id == user["id"])
    )

    current_user.group = await db_session.scalar(
        select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.MODERATOR)
    )

    await db_session.commit()

    movie_payload = {
        "name": "Test",
        "date": "2020-08-20",
        "score": 89,
        "overview": "Tested",
        "status": "Released",
        "budget": "12345654",
        "revenue": "76543245",
        "country": "USA",
        "genres": ["Test Genre"],
        "actors": ["Test Actor"],
        "languages": ["Test Language"],
    }

    response = await client.post(
        f"{CINEMA_URL}/movies/",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json=movie_payload,
    )

    assert response.status_code == 201

    response = await client.get(f"{CINEMA_URL}/movies/?page=2&per_page=10")

    assert response.status_code == 404
    assert response.json()["detail"] == "No movies found."


@pytest.mark.parametrize(
    "query",
    [
        "page=0&per_page=10",
        "page=-1&per_page=10",
        "page=1&per_page=0",
        "page=1&per_page=101",
    ],
)
async def test_get_movie_list_invalid_pagination(
    client: AsyncClient,
    query: str,
):
    response = await client.get(f"{CINEMA_URL}/movies/?{query}")

    assert response.status_code == 422


async def test_update_movie_success(
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

    movie_payload = {
        "name": "Test",
        "date": "2020-08-20",
        "score": 89,
        "overview": "Tested",
        "status": "Released",
        "budget": "12345654",
        "revenue": "76543245",
        "country": "USA",
        "genres": ["Test Genre"],
        "actors": ["Test Actor 1", "Test Actor 2"],
        "languages": ["Test Language"],
    }

    response = await client.post(
        f"{CINEMA_URL}/movies/",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json=movie_payload,
    )

    assert response.status_code == 201

    movie_id = response.json()["id"]

    update_payload = {
        "name": "Updated Test",
        "score": 95,
        "overview": "Updated overview",
        "budget": "20000000",
    }

    response = await client.patch(
        f"{CINEMA_URL}/movies/{movie_id}/",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json=update_payload,
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Movie updated successfully."

    movie = await db_session.scalar(select(MovieModel).where(MovieModel.id == movie_id))

    assert movie is not None
    assert movie.name == "Updated Test"
    assert movie.score == 95
    assert movie.overview == "Updated overview"
    assert float(movie.budget) == 20000000

    assert str(movie.date) == "2020-08-20"
    assert float(movie.revenue) == 76543245


async def test_default_user_update_movie_forbidden(
    client: AsyncClient, authenticated_user
):
    access_token = authenticated_user[1]

    response = await client.patch(
        f"{CINEMA_URL}/movies/1/",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json={
            "name": "Updated Test",
        },
    )

    assert response.status_code == 403

    detail = response.json()["detail"]
    assert detail == "You do not have permission to perform this action."


async def test_unauthenticated_user_update_movie_not_allowed(
    client: AsyncClient,
):
    response = await client.patch(
        f"{CINEMA_URL}/movies/1/",
        json={
            "name": "Updated Test",
        },
    )

    assert response.status_code == 401

    detail = response.json()["detail"]
    assert detail == "Not authenticated"


async def test_update_movie_not_found(
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

    response = await client.patch(
        f"{CINEMA_URL}/movies/99999/",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json={
            "name": "Updated Test",
        },
    )

    assert response.status_code == 404

    detail = response.json()["detail"]
    assert detail == "Movie with the given ID was not found."


async def test_update_movie_without_fields_error(
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

    movie_payload = {
        "name": "Test",
        "date": "2020-08-20",
        "score": 89,
        "overview": "Tested",
        "status": "Released",
        "budget": "12345654",
        "revenue": "76543245",
        "country": "USA",
        "genres": ["Test Genre"],
        "actors": ["Test Actor 1", "Test Actor 2"],
        "languages": ["Test Language"],
    }

    response = await client.post(
        f"{CINEMA_URL}/movies/",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json=movie_payload,
    )

    assert response.status_code == 201

    movie_id = response.json()["id"]

    response = await client.patch(
        f"{CINEMA_URL}/movies/{movie_id}/",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json={},
    )

    assert response.status_code == 400

    detail = response.json()["detail"]
    assert detail == "No fields were provided for update."


async def test_update_movie_with_date_more_than_one_year_in_future_error(
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

    movie_payload = {
        "name": "Test",
        "date": "2020-08-20",
        "score": 89,
        "overview": "Tested",
        "status": "Released",
        "budget": "12345654",
        "revenue": "76543245",
        "country": "USA",
        "genres": ["Test Genre"],
        "actors": ["Test Actor 1", "Test Actor 2"],
        "languages": ["Test Language"],
    }

    response = await client.post(
        f"{CINEMA_URL}/movies/",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json=movie_payload,
    )

    assert response.status_code == 201

    movie_id = response.json()["id"]

    incorrect_date = str(date.today() + timedelta(days=366))

    response = await client.patch(
        f"{CINEMA_URL}/movies/{movie_id}/",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json={
            "date": incorrect_date,
        },
    )

    assert response.status_code == 422

    detail = response.json()["detail"]

    assert (
        "Release date cannot be more than one year in the future." in detail[0]["msg"]
    )


async def test_update_movie_with_same_name_and_date_error(
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

    first_movie_payload = {
        "name": "Test One",
        "date": "2020-08-20",
        "score": 89,
        "overview": "Tested",
        "status": "Released",
        "budget": "12345654",
        "revenue": "76543245",
        "country": "USA",
        "genres": ["Test Genre"],
        "actors": ["Test Actor 1"],
        "languages": ["Test Language"],
    }

    second_movie_payload = {
        "name": "Test Two",
        "date": "2021-08-20",
        "score": 80,
        "overview": "Tested",
        "status": "Released",
        "budget": "10000000",
        "revenue": "20000000",
        "country": "USA",
        "genres": ["Test Genre"],
        "actors": ["Test Actor 2"],
        "languages": ["Test Language"],
    }

    response_1 = await client.post(
        f"{CINEMA_URL}/movies/",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json=first_movie_payload,
    )

    assert response_1.status_code == 201

    response_2 = await client.post(
        f"{CINEMA_URL}/movies/",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json=second_movie_payload,
    )

    assert response_2.status_code == 201

    second_movie_id = response_2.json()["id"]

    response = await client.patch(
        f"{CINEMA_URL}/movies/{second_movie_id}/",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json={
            "name": first_movie_payload["name"],
            "date": first_movie_payload["date"],
        },
    )

    assert response.status_code == 409

    detail = response.json()["detail"]

    assert detail == (
        f"A movie with the name '{first_movie_payload['name']}' "
        f"and release date '{first_movie_payload['date']}' already exists."
    )
