import pytest


from httpx import AsyncClient
from io import BytesIO

from PIL import Image

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
