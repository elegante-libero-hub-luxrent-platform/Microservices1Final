"""
Database service layer providing CRUD operations for User and Profile entities.
This layer abstracts database operations from the FastAPI routes.
"""

from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional, Tuple
import hashlib

from models.orm import UserDB, ProfileDB
from models.user import UserCreate, UserUpdate, UserRead
from models.profile import ProfileCreate, ProfileUpdate, ProfileRead


class UserService:
    """Service for User database operations."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using SHA-256 (demo only, use bcrypt in production)."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def create_user(db: Session, user_create: UserCreate) -> UserRead:
        """Create a new user."""
        db_user = UserDB(
            name=user_create.name,
            email=user_create.email,
            phone=user_create.phone,
            membership_tier=user_create.membership_tier,
            password_hash=UserService.hash_password(user_create.password.get_secret_value())
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return UserService._db_to_read(db_user)
    
    @staticmethod
    def get_user(db: Session, user_id: UUID) -> Optional[UserRead]:
        """Get user by ID."""
        db_user = db.query(UserDB).filter(UserDB.id == user_id).first()
        return UserService._db_to_read(db_user) if db_user else None
    
    @staticmethod
    def list_users(
        db: Session,
        name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        membership_tier: Optional[str] = None,
        offset: int = 0,
        limit: int = 10
    ) -> Tuple[List[UserRead], int]:
        """List users with filters and pagination."""
        query = db.query(UserDB)
        
        if name is not None:
            query = query.filter(UserDB.name == name)
        if email is not None:
            query = query.filter(UserDB.email.ilike(f"%{email}%"))  # Case-insensitive
        if phone is not None:
            query = query.filter(UserDB.phone == phone)
        if membership_tier is not None:
            query = query.filter(UserDB.membership_tier == membership_tier)
        
        total = query.count()
        db_users = query.offset(offset).limit(limit).all()
        users = [UserService._db_to_read(u) for u in db_users]
        return users, total
    
    @staticmethod
    def update_user(db: Session, user_id: UUID, user_update: UserUpdate) -> Optional[UserRead]:
        """Update a user."""
        db_user = db.query(UserDB).filter(UserDB.id == user_id).first()
        if not db_user:
            return None
        
        update_data = user_update.model_dump(exclude_unset=True, exclude={"new_password"})
        for field, value in update_data.items():
            if value is not None:
                setattr(db_user, field, value)
        
        if user_update.new_password:
            db_user.password_hash = UserService.hash_password(user_update.new_password.get_secret_value())
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return UserService._db_to_read(db_user)
    
    @staticmethod
    def delete_user(db: Session, user_id: UUID) -> bool:
        """Delete a user."""
        db_user = db.query(UserDB).filter(UserDB.id == user_id).first()
        if not db_user:
            return False
        
        db.delete(db_user)
        db.commit()
        return True
    
    @staticmethod
    def user_exists_by_email(db: Session, email: str, exclude_id: Optional[UUID] = None) -> bool:
        """Check if email exists."""
        query = db.query(UserDB).filter(UserDB.email.ilike(email))
        if exclude_id:
            query = query.filter(UserDB.id != exclude_id)
        return query.first() is not None
    
    @staticmethod
    def user_exists_by_phone(db: Session, phone: str, exclude_id: Optional[UUID] = None) -> bool:
        """Check if phone exists."""
        query = db.query(UserDB).filter(UserDB.phone == phone)
        if exclude_id:
            query = query.filter(UserDB.id != exclude_id)
        return query.first() is not None
    
    @staticmethod
    def _db_to_read(db_user: Optional[UserDB]) -> Optional[UserRead]:
        """Convert database model to Pydantic read model."""
        if not db_user:
            return None
        return UserRead(
            id=db_user.id,
            name=db_user.name,
            email=db_user.email,
            phone=db_user.phone,
            membership_tier=db_user.membership_tier
        )


class ProfileService:
    """Service for Profile database operations."""
    
    @staticmethod
    def create_profile(db: Session, profile_create: ProfileCreate) -> ProfileRead:
        """Create a new profile."""
        db_profile = ProfileDB(
            user_id=profile_create.user_id,
            username=profile_create.username,
            display_name=profile_create.display_name,
            avatar_url=profile_create.avatar_url,
            bio=profile_create.bio,
            style_tags=profile_create.style_tags
        )
        db_profile.set_style_tags(profile_create.style_tags)
        db.add(db_profile)
        db.commit()
        db.refresh(db_profile)
        return ProfileService._db_to_read(db_profile)
    
    @staticmethod
    def get_profile(db: Session, profile_id: UUID) -> Optional[ProfileRead]:
        """Get profile by ID."""
        db_profile = db.query(ProfileDB).filter(ProfileDB.id == profile_id).first()
        return ProfileService._db_to_read(db_profile) if db_profile else None
    
    @staticmethod
    def list_profiles(
        db: Session,
        user_id: Optional[UUID] = None,
        username: Optional[str] = None,
        offset: int = 0,
        limit: int = 10
    ) -> Tuple[List[ProfileRead], int]:
        """List profiles with filters and pagination."""
        query = db.query(ProfileDB)
        
        if user_id is not None:
            query = query.filter(ProfileDB.user_id == user_id)
        if username is not None:
            query = query.filter(ProfileDB.username.ilike(f"%{username}%"))  # Case-insensitive
        
        total = query.count()
        db_profiles = query.offset(offset).limit(limit).all()
        profiles = [ProfileService._db_to_read(p) for p in db_profiles]
        return profiles, total
    
    @staticmethod
    def update_profile(db: Session, profile_id: UUID, profile_update: ProfileUpdate) -> Optional[ProfileRead]:
        """Update a profile."""
        db_profile = db.query(ProfileDB).filter(ProfileDB.id == profile_id).first()
        if not db_profile:
            return None
        
        update_data = profile_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                if field == "style_tags":
                    db_profile.set_style_tags(value)
                else:
                    setattr(db_profile, field, value)
        
        db.add(db_profile)
        db.commit()
        db.refresh(db_profile)
        return ProfileService._db_to_read(db_profile)
    
    @staticmethod
    def delete_profile(db: Session, profile_id: UUID) -> bool:
        """Delete a profile."""
        db_profile = db.query(ProfileDB).filter(ProfileDB.id == profile_id).first()
        if not db_profile:
            return False
        
        db.delete(db_profile)
        db.commit()
        return True
    
    @staticmethod
    def username_exists(db: Session, username: str, exclude_id: Optional[UUID] = None) -> bool:
        """Check if username exists."""
        query = db.query(ProfileDB).filter(ProfileDB.username.ilike(username))
        if exclude_id:
            query = query.filter(ProfileDB.id != exclude_id)
        return query.first() is not None
    
    @staticmethod
    def profile_exists_for_user(db: Session, user_id: UUID) -> bool:
        """Check if user already has a profile."""
        return db.query(ProfileDB).filter(ProfileDB.user_id == user_id).first() is not None
    
    @staticmethod
    def _db_to_read(db_profile: Optional[ProfileDB]) -> Optional[ProfileRead]:
        """Convert database model to Pydantic read model."""
        if not db_profile:
            return None
        return ProfileRead(
            id=db_profile.id,
            user_id=db_profile.user_id,
            username=db_profile.username,
            display_name=db_profile.display_name,
            avatar_url=db_profile.avatar_url,
            bio=db_profile.bio,
            style_tags=db_profile.get_style_tags()
        )
