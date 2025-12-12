from __future__ import annotations
from typing import Literal, Annotated, Optional, List, Dict, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, HttpUrl, StringConstraints

# Username: letters, digits, underscore, 3-32 chars (case-insensitive uniqueness enforced in service)
Username = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_]{3,32}$", min_length=3, max_length=32)]

class ProfileBase(BaseModel):
    user_id: UUID = Field(..., description="Owner user ID (foreign key to User)")
    username: Username = Field(..., description="Public unique handle", json_schema_extra={"example": "mamba_24"})
    display_name: str | None = Field(None, description="Display name", json_schema_extra={"example": "Black Mamba"})
    avatar_url: HttpUrl | None = Field(None, description="Avatar URL", json_schema_extra={"example": "https://cdn.example.com/avatars/kb.png"})
    bio: str | None = Field(None, description="Short bio (max 280 chars)", json_schema_extra={"example": "Love hoops & craftsmanship."}, max_length=114)
    # Optional fashion-related preferences
    style_tags: List[str] = Field(default_factory=list, description="Preferred styles/tags", json_schema_extra={"example": ["street", "minimal"]})

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "username": "mamba_24",
                    "display_name": "Black Mamba",
                    "avatar_url": "https://mambaout.com/avatars/kb.png",
                    "bio": "Love to drive helicopter.",
                    "style_tags": ["burned", "explosion"]
                }
            ]
        }
    }

class ProfileCreate(ProfileBase):
    """Create payload for Profile (same fields as base)."""
    pass

class ProfileUpdate(BaseModel):
    """Partial update; only provided fields will be changed."""
    username: Username | None = None
    display_name: str | None = None
    avatar_url: HttpUrl | None = None
    bio: str | None = Field(None, max_length=280)
    style_tags: List[str] | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"display_name": "Kobe B."},
                {"bio": "Elegance in crashing."},
                {"style_tags": ["Roasted", "crispy"]}
            ]
        }
    }

class ProfileRead(ProfileBase):
    """Server-side representation returned to clients."""
    id: UUID = Field(default_factory=uuid4, description="Profile ID", json_schema_extra={"example": "9f2c33a4-9b56-4c53-8c48-8c8d8d9d9d9d"})
    links: Optional[Dict[str, Any]] = Field(default=None, alias="_links", description="HATEOAS links", serialization_alias="_links")
    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": "9f2c33a4-9b56-4c53-8c48-8c8d8d9d9d9d",
                    "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "username": "mamba_24",
                    "display_name": "Black Mamba",
                    "avatar_url": "https://mambaout.com/avatars/kb.png",
                    "bio": "Love to drive helicopter.",
                    "style_tags": ["burned", "explosion"],
                    "_links": {
                        "self": "/profiles/9f2c33a4-9b56-4c53-8c48-8c8d8d9d9d9d",
                        "user": "/users/3fa85f64-5717-4562-b3fc-2c963f66afa6"
                    }
                }
            ]
        }
    }
