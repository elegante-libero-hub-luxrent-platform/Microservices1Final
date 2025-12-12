"""
SQLAlchemy ORM models for User and Profile entities.
These models map Python classes to database tables.
"""

from sqlalchemy import Column, String, UUID, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator
import uuid
from datetime import datetime
import json

from database import Base


class GUID(TypeDecorator):
    """
    Platform-independent GUID type.
    Uses CHAR(32) for SQLite, CHAR(36) for MySQL.
    """
    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


class UserDB(Base):
    """User database model."""
    __tablename__ = "users"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), unique=True, nullable=False)
    membership_tier = Column(String(20), default="FREE", index=True)
    password_hash = Column(String(255), nullable=False)  # Hashed password
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    profile = relationship("ProfileDB", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<UserDB(id={self.id}, email={self.email}, name={self.name})>"


class ProfileDB(Base):
    """Profile database model."""
    __tablename__ = "profiles"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    username = Column(String(32), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=True)
    avatar_url = Column(String(512), nullable=True)
    bio = Column(String(280), nullable=True)
    style_tags = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user = relationship("UserDB", back_populates="profile")

    def get_style_tags(self):
        """Deserialize style_tags from JSON."""
        if not self.style_tags:
            return []
        try:
            return json.loads(self.style_tags)
        except:
            return []

    def set_style_tags(self, tags):
        """Serialize style_tags to JSON."""
        self.style_tags = json.dumps(tags) if tags else None

    def __repr__(self):
        return f"<ProfileDB(id={self.id}, user_id={self.user_id}, username={self.username})>"
