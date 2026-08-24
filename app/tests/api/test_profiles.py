import pytest


from httpx import AsyncClient
from io import BytesIO

from PIL import Image
from sqlalchemy import select

from app.models.accounts import UserModel, UserGroupModel, UserGroupEnum

pytestmark = pytest.mark.anyio


def create_test_image() -> bytes:
    buffer = BytesIO()

    image = Image.new(
        "RGB",
        (10, 10),
    )

    image.save(
        buffer,
        format="JPEG",
    )

    return buffer.getvalue()


async def test_create_profile_success(
    client: AsyncClient,
    authenticated_user,
    fake_s3_storage,
):
    user, access_token = authenticated_user

    image_bytes = create_test_image()

    response = await client.post(
        f"/api/users/{user['id']}/profile/",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        data={
            "first_name": "TestFirst",
            "last_name": "TestLast",
            "gender": "man",
            "date_of_birth": "2000-01-01",
            "info": "Test profile",
        },
        files={
            "avatar": (
                "avatar.jpg",
                image_bytes,
                "image/jpeg",
            ),
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["user_id"] == user["id"]
    assert data["first_name"] == "testfirst"
    assert data["last_name"] == "testlast"

    assert len(fake_s3_storage.files) == 1


async def test_get_profile_success(
    client: AsyncClient,
    authenticated_user,
    fake_s3_storage,
):
    user, access_token = authenticated_user

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    image_bytes = create_test_image()

    create_response = await client.post(
        f"/api/users/{user['id']}/profile/",
        headers=headers,
        data={
            "first_name": "TestFirst",
            "last_name": "TestLast",
            "gender": "man",
            "date_of_birth": "2000-01-01",
            "info": "Test profile",
        },
        files={
            "avatar": (
                "avatar.jpg",
                image_bytes,
                "image/jpeg",
            ),
        },
    )

    assert create_response.status_code == 201

    response = await client.get(
        f"/api/users/{user['id']}/profile/",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["user_id"] == user["id"]
    assert data["first_name"] == "testfirst"
    assert data["last_name"] == "testlast"
    assert data["gender"] == "man"
    assert data["date_of_birth"] == "2000-01-01"
    assert data["info"] == "Test profile"
    assert data["avatar"].startswith("http://test-storage/")


async def test_add_movie_to_favorites_success(
    client: AsyncClient,
    db_session,
    authenticated_user,
    fake_s3_storage,
):
    user, access_token = authenticated_user

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    image_bytes = create_test_image()

    profile_response = await client.post(
        f"/api/users/{user['id']}/profile/",
        headers=headers,
        data={
            "first_name": "TestFirst",
            "last_name": "TestLast",
            "gender": "man",
            "date_of_birth": "2000-01-01",
            "info": "Test profile",
        },
        files={
            "avatar": (
                "avatar.jpg",
                image_bytes,
                "image/jpeg",
            ),
        },
    )

    assert profile_response.status_code == 201

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

    movie_response = await client.post(
        "/api/cinema/movies/",
        headers=headers,
        json=movie_payload,
    )

    assert movie_response.status_code == 201

    movie_data = movie_response.json()

    response = await client.put(
        f"/api/cinema/movies/{movie_data['id']}/favorite/",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Movie added to favorites successfully."

    profile_response = await client.get(
        f"/api/users/{user['id']}/profile/",
        headers=headers,
    )

    assert profile_response.status_code == 200

    profile_data = profile_response.json()

    assert {
        "id": movie_data["id"],
        "name": movie_data["name"],
    } in profile_data["favorite_movies"]


async def test_add_same_movie_to_favorites_twice(
    client: AsyncClient,
    db_session,
    authenticated_user,
    fake_s3_storage,
):
    user, access_token = authenticated_user

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    image_bytes = create_test_image()

    profile_response = await client.post(
        f"/api/users/{user['id']}/profile/",
        headers=headers,
        data={
            "first_name": "TestFirst",
            "last_name": "TestLast",
            "gender": "man",
            "date_of_birth": "2000-01-01",
            "info": "Test profile",
        },
        files={
            "avatar": (
                "avatar.jpg",
                image_bytes,
                "image/jpeg",
            ),
        },
    )

    assert profile_response.status_code == 201

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
        "actors": ["Test Actor 1"],
        "languages": ["Test Language"],
    }

    movie_response = await client.post(
        "/api/cinema/movies/",
        headers=headers,
        json=movie_payload,
    )

    assert movie_response.status_code == 201

    movie_id = movie_response.json()["id"]

    response_1 = await client.put(
        f"/api/cinema/movies/{movie_id}/favorite/",
        headers=headers,
    )

    response_2 = await client.put(
        f"/api/cinema/movies/{movie_id}/favorite/",
        headers=headers,
    )

    assert response_1.status_code == 200
    assert response_2.status_code == 200

    profile_response = await client.get(
        f"/api/users/{user['id']}/profile/",
        headers=headers,
    )

    favorite_movies = profile_response.json()["favorite_movies"]

    assert len([movie for movie in favorite_movies if movie["id"] == movie_id]) == 1


async def test_remove_movie_from_favorites_success(
    client: AsyncClient,
    db_session,
    authenticated_user,
    fake_s3_storage,
):
    user, access_token = authenticated_user

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    image_bytes = create_test_image()

    profile_response = await client.post(
        f"/api/users/{user['id']}/profile/",
        headers=headers,
        data={
            "first_name": "TestFirst",
            "last_name": "TestLast",
            "gender": "man",
            "date_of_birth": "2000-01-01",
            "info": "Test profile",
        },
        files={
            "avatar": (
                "avatar.jpg",
                image_bytes,
                "image/jpeg",
            ),
        },
    )

    assert profile_response.status_code == 201

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
        "actors": ["Test Actor 1"],
        "languages": ["Test Language"],
    }

    movie_response = await client.post(
        "/api/cinema/movies/",
        headers=headers,
        json=movie_payload,
    )

    assert movie_response.status_code == 201

    movie_id = movie_response.json()["id"]

    response = await client.put(
        f"/api/cinema/movies/{movie_id}/favorite/",
        headers=headers,
    )

    assert response.status_code == 200

    response = await client.delete(
        f"/api/cinema/movies/{movie_id}/favorite/",
        headers=headers,
    )

    assert response.status_code == 204

    profile_response = await client.get(
        f"/api/users/{user['id']}/profile/",
        headers=headers,
    )

    assert profile_response.status_code == 200

    favorite_movies = profile_response.json()["favorite_movies"]

    assert all(movie["id"] != movie_id for movie in favorite_movies)


async def test_add_not_existing_movie_to_favorites_error(
    client: AsyncClient,
    authenticated_user,
    fake_s3_storage,
):
    user, access_token = authenticated_user

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    image_bytes = create_test_image()

    profile_response = await client.post(
        f"/api/users/{user['id']}/profile/",
        headers=headers,
        data={
            "first_name": "TestFirst",
            "last_name": "TestLast",
            "gender": "man",
            "date_of_birth": "2000-01-01",
            "info": "Test profile",
        },
        files={
            "avatar": (
                "avatar.jpg",
                image_bytes,
                "image/jpeg",
            ),
        },
    )

    assert profile_response.status_code == 201

    response = await client.put(
        "/api/cinema/movies/99999/favorite/",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Movie with the given ID was not found."


async def test_add_movie_to_favorites_without_profile_error(
    client: AsyncClient,
    authenticated_user,
):
    user, access_token = authenticated_user

    response = await client.put(
        "/api/cinema/movies/1/favorite/",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User profile not found."
