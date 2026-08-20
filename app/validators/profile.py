import re
from datetime import date
from io import BytesIO

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

SUPPORTED_IMAGE_FORMATS = {"JPEG", "PNG"}
MAX_FILE_SIZE = 1024 * 1024  # 1 MB


def validate_name(name: str) -> None:
    if re.fullmatch(r"[A-Za-z]+", name) is None:
        raise ValueError(f"{name} contains non-English letters or invalid characters.")


def validate_image(avatar: UploadFile) -> None:
    contents = avatar.file.read()

    try:
        if len(contents) > MAX_FILE_SIZE:
            raise ValueError("Image size exceeds 1 MB.")

        image = Image.open(BytesIO(contents))

        if image.format not in SUPPORTED_IMAGE_FORMATS:
            raise ValueError(
                f"Unsupported image format: {image.format}. "
                f"Supported formats: {', '.join(SUPPORTED_IMAGE_FORMATS)}."
            )

        image.verify()

    except UnidentifiedImageError:
        raise ValueError("Invalid image format.")

    except OSError:
        raise ValueError("Invalid or corrupted image.")

    finally:
        avatar.file.seek(0)


def validate_birth_date(birth_date: date) -> None:
    today = date.today()

    if birth_date > today:
        raise ValueError("Birth date cannot be in the future.")

    if birth_date.year <= 1900:
        raise ValueError("Invalid birth date - year must be greater than 1900.")

    age = (
        today.year
        - birth_date.year
        - ((today.month, today.day) < (birth_date.month, birth_date.day))
    )

    if age < 18:
        raise ValueError("You must be at least 18 years old.")
