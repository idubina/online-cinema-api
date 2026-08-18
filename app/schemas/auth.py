from pydantic import BaseModel, EmailStr, field_validator, ConfigDict

from app.validators import accounts as accounts_validators


class BaseEmailSchema(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        return value.lower()


class BaseEmailPasswordSchema(BaseEmailSchema):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        return accounts_validators.validate_password_strength(value)


class UserRegistrationRequestSchema(BaseEmailPasswordSchema):
    pass


class UserRegistrationResponseSchema(BaseModel):
    id: int
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class UserActivationRequestSchema(BaseEmailSchema):
    token: str


class MessageResponseSchema(BaseModel):
    message: str
