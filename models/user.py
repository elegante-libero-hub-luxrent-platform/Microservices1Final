from __future__ import annotations
from typing import Literal, Annotated, Dict, Any, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, EmailStr, SecretStr, StringConstraints


# US-only E.164 phone: +1XXXXXXXXXX
USPhone = Annotated[
    str,
    StringConstraints(pattern=r"^\+1\d{10}$", strip_whitespace=True)
]

class UserBase(BaseModel):
    name: str = Field(..., description="Name for user", json_schema_extra={"example": "Kobe Bryant"})
    email: EmailStr = Field(..., description="email for user", json_schema_extra={"example": "helicopter@crash.com"})
    phone: USPhone = Field(..., description="US phone number", json_schema_extra={"example": "+11234567890"})
    membership_tier: Literal["FREE", "PRO", "PROMAX"] = Field(default="FREE", description="level", json_schema_extra={"example": "FREE"})

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Kobe Bryant",
                    "email": "kobe24@helicopter.com",
                    "phone": "+11234567890",
                    "membership_tier": "PRO"
                }
            ]
        }
    }

class UserCreate(UserBase):
    password: SecretStr = Field(..., description="account password for user", json_schema_extra={"example": "MambaOut"})
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Kobe Bryant",
                    "email": "kobe24@example.com",
                    "phone": "+11234567890",
                    "membership_tier": "PRO",
                    "password": "MambaOut_24"
                }
            ]
        }
    }

class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: USPhone | None = None
    membership_tier: Literal["FREE","PRO","PROMAX"] | None = None
    new_password: SecretStr | None = None
    model_config = {
        "json_schema_extra": {
            "examples": [
                {"name": "Black Mamba"},
                {"membership_tier": "PROMAX"},
                {"new_password": "DonotTakeHelicpoter"}
            ]
        }
    }

class UserRead(UserBase):
    id: UUID = Field(default_factory=uuid4, description="User unique ID", json_schema_extra={"example": "11451419-1981-0114-5141-919810114514"})
    links: Optional[Dict[str, Any]] = Field(default=None, alias="_links", description="HATEOAS links", serialization_alias="_links")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": "11451419-1981-0114-5141-919810114514",
                    "name": "Kobe Bryant",
                    "email": "kobe24@example.com",
                    "phone": "+11234567890",
                    "membership_tier": "PRO",
                    "_links": {
                        "self": "/users/11451419-1981-0114-5141-919810114514",
                        "orders": "/orders?userId=11451419-1981-0114-5141-919810114514",
                        "profile": "/profiles?userId=11451419-1981-0114-5141-919810114514"
                    }
                }
            ]
        }
    }