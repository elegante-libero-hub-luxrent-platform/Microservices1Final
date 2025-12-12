from __future__ import annotations

import os
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import FastAPI, HTTPException, Response, Depends
from fastapi import Query, Path, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from auth import router as auth_router, require_jwt

from models.user import UserCreate, UserUpdate, UserRead
from models.profile import ProfileCreate, ProfileRead, ProfileUpdate
from utils.etag import etag_from_model, should_return_304, should_process_request
from utils.pagination import paginate, PaginationParams

from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# 加载 .env（无论是 main.py 还是 main_db.py，只要 import auth 都会执行这里）
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# -----------------------------------------------------------------------------
# 配置
# -----------------------------------------------------------------------------

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-secret-change-me")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "60"))

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI")

port = int(os.environ.get("FASTAPIPORT", 8000))

# -----------------------------------------------------------------------------
# In-memory "databases"
#   - `users` holds public-safe user data (UserRead)
#   - `user_secrets` holds sensitive data (plaintext password for demo)
# -----------------------------------------------------------------------------
users: Dict[UUID, UserRead] = {}
user_secrets: Dict[UUID, dict] = {}  # { user_id: {"password": "<plaintext>"} }
profiles: Dict[UUID, ProfileRead] = {}            # primary store by profile_id
profiles_by_user: Dict[UUID, UUID] = {}           # ensure 1:1 (user_id -> profile_id)

app = FastAPI(
    title="Person/Address API",
    description="Demo FastAPI app using Pydantic v2 models for Person and Address",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"], 
)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET_KEY", "dev-session-secret"),
)


app.include_router(auth_router)

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------
def _email_exists(email: str, exclude_id: Optional[UUID] = None) -> bool:
    """
    Check whether an email already exists among users.
    `exclude_id` lets you ignore a specific user (useful during updates).
    """
    e = email.lower()
    for u in users.values():
        if u.email.lower() == e and (exclude_id is None or u.id != exclude_id):
            return True
    return False


def _phone_exists(phone: str, exclude_id: Optional[UUID] = None) -> bool:
    """
    Check whether a phone number already exists among users.
    `exclude_id` lets you ignore a specific user (useful during updates).
    """
    for u in users.values():
        if u.phone == phone and (exclude_id is None or u.id != exclude_id):
            return True
    return False


def _find_user_by_email(email: str) -> Optional[UserRead]:
    """
    Find a user object by email (case-insensitive).
    Returns the UserRead instance or None if not found.
    """
    e = email.lower()
    for u in users.values():
        if u.email.lower() == e:
            return u
    return None

def _username_exists(username: str, exclude_id: Optional[UUID] = None) -> bool:
    """
    Check case-insensitive uniqueness for username.
    """
    target = username.lower()
    for pid, prof in profiles.items():
        if prof.username.lower() == target and (exclude_id is None or pid != exclude_id):
            return True
    return False

def _assert_user_exists(user_id: UUID):
    """
    Ensure the referenced user exists in the in-memory users DB.
    """
    if user_id not in users:
        raise HTTPException(status_code=400, detail="User does not exist")

def _assert_user_has_no_profile(user_id: UUID):
    """
    Ensure 1:1 relationship: a user can have only one profile.
    """
    if user_id in profiles_by_user:
        raise HTTPException(status_code=400, detail="User already has a profile")


def _build_user_with_links(user: UserRead) -> UserRead:
    """Add HATEOAS links to a UserRead response."""
    user.links = {
        "self": f"/users/{user.id}",
        "orders": f"/orders?userId={user.id}",
        "profile": f"/profiles?userId={user.id}"
    }
    return user


def _build_profile_with_links(profile: ProfileRead) -> ProfileRead:
    """Add HATEOAS links to a ProfileRead response."""
    profile.links = {
        "self": f"/profiles/{profile.id}",
        "user": f"/users/{profile.user_id}"
    }
    return profile
# -----------------------------------------------------------------------------
# Users CRUD
# -----------------------------------------------------------------------------
@app.post("/users", response_model=UserRead, status_code=201, tags=["users"])
def create_user(
    payload: UserCreate,
    response: Response,
    current_user: dict = Depends(require_jwt),
):
    """
    Create a new user.
    - Enforces email and phone uniqueness.
    - Persists public fields in `users` (UserRead).
    - Stores plaintext password in `user_secrets` (DEMO ONLY).
    - Returns 201 Created with Location header.
    """
    if _email_exists(payload.email):
        raise HTTPException(status_code=400, detail="Email already exists")
    if _phone_exists(payload.phone):
        raise HTTPException(status_code=400, detail="Phone already exists")

    # Build the public-safe UserRead (no password inside)
    user = UserRead(**payload.model_dump(exclude={"password"}))
    users[user.id] = user

    # Store plaintext password for demo purposes
    user_secrets[user.id] = {"password": payload.password.get_secret_value()}

    # Set Location header per RFC 7231
    response.headers["Location"] = f"/users/{user.id}"
    
    # Add HATEOAS links
    user = _build_user_with_links(user)

    return user


@app.get("/users", tags=["users"])
def list_users(
    name: Optional[str] = Query(None, description="Filter by exact name"),
    email: Optional[str] = Query(None, description="Filter by exact email (case-insensitive)"),
    phone: Optional[str] = Query(None, description="Filter by exact phone"),
    membership_tier: Optional[str] = Query(None, description='Filter by tier: "FREE"|"PRO"|"PROMAX"'),
    pageSize: int = Query(10, ge=1, le=100, description="Number of items per page"),
    pageToken: Optional[str] = Query(None, description="Opaque pagination token"),
):
    """
    List users with optional exact-match filters and pagination.
    Supports cursor-based pagination with opaque pageToken.
    """
    results = list(users.values())

    if name is not None:
        results = [u for u in results if u.name == name]
    if email is not None:
        e = email.lower()
        results = [u for u in results if u.email.lower() == e]
    if phone is not None:
        results = [u for u in results if u.phone == phone]
    if membership_tier is not None:
        results = [u for u in results if u.membership_tier == membership_tier]

    # Add HATEOAS links to all users
    results = [_build_user_with_links(u) for u in results]
    
    # Paginate results
    page_items, next_token = paginate(results, pageSize, pageToken)
    
    # Build response with pagination links
    return {
        "items": page_items,
        "pageSize": pageSize,
        "pageToken": pageToken,
        "_links": {
            "self": f"/users?pageSize={pageSize}" + (f"&pageToken={pageToken}" if pageToken else ""),
            "next": f"/users?pageSize={pageSize}&pageToken={next_token}" if next_token else None
        }
    }


@app.get("/users/{user_id}", tags=["users"])
def get_user(
    user_id: UUID = Path(..., description="User ID (UUID)"),
    if_none_match: Optional[str] = Header(None, description="ETag from previous request")
):
    """
    Retrieve a single user by ID.
    Supports conditional request with If-None-Match (ETag).
    Returns 304 Not Modified if ETag matches.
    """
    if user_id not in users:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = users[user_id]
    current_etag = etag_from_model(user)
    
    # Check If-None-Match (RFC 7232)
    if should_return_304(if_none_match, current_etag):
        raise HTTPException(status_code=304, detail="Not Modified")
    
    # Add HATEOAS links
    user = _build_user_with_links(user)
    
    # Return JSONResponse with ETag header
    return JSONResponse(
        status_code=200,
        content=user.model_dump(mode='json'),
        headers={"ETag": current_etag, "Cache-Control": "max-age=3600"}
    )


@app.patch("/users/{user_id}", tags=["users"])
def update_user(
    user_id: UUID,
    patch: UserUpdate,
    if_match: Optional[str] = Header(None, description="ETag for conditional update")
):
    """
    Partially update a user.
    - Only applies fields present in the request body (PATCH semantics).
    - Enforces uniqueness if email/phone is being changed.
    - Updates plaintext password if `new_password` is provided.
    - Supports conditional update with If-Match (ETag).
    - Returns 412 Precondition Failed if ETag does not match.
    """
    if user_id not in users:
        raise HTTPException(status_code=404, detail="User not found")

    current_user = users[user_id]
    current_etag = etag_from_model(current_user)
    
    # Check If-Match (RFC 7232)
    if not should_process_request(if_match, current_etag):
        raise HTTPException(status_code=412, detail="Precondition Failed")

    current = current_user.model_dump()
    changes = patch.model_dump(exclude_unset=True, exclude={"new_password"})

    # Uniqueness checks for fields that may change
    new_email = changes.get("email")
    if new_email and _email_exists(new_email, exclude_id=user_id):
        raise HTTPException(status_code=400, detail="Email already exists")

    new_phone = changes.get("phone")
    if new_phone and _phone_exists(new_phone, exclude_id=user_id):
        raise HTTPException(status_code=400, detail="Phone already exists")

    # Merge and rebuild UserRead
    current.update(changes)
    users[user_id] = UserRead(**current)

    # Update plaintext password if provided
    if patch.new_password is not None:
        user_secrets[user_id] = {"password": patch.new_password.get_secret_value()}

    # Add HATEOAS links
    user = _build_user_with_links(users[user_id])
    
    # Return JSONResponse with new ETag header
    new_etag = etag_from_model(user)
    return JSONResponse(
        status_code=200,
        content=user.model_dump(mode='json'),
        headers={"ETag": new_etag}
    )


@app.delete("/users/{user_id}", status_code=204, tags=["users"])
def delete_user(
    user_id: UUID,
    current_user: dict = Depends(require_jwt),
):
    """
    Delete a user and its associated secret record.
    """
    if user_id not in users:
        raise HTTPException(status_code=404, detail="User not found")
    users.pop(user_id, None)
    user_secrets.pop(user_id, None)
    return None
# -----------------------------------------------------------------------------
# Users CRUD Endpoint
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Profile CRUD
# -----------------------------------------------------------------------------
@app.post("/profiles", response_model=ProfileRead, status_code=201, tags=["profiles"])
def create_profile(payload: ProfileCreate, response: Response):
    """
    Create profile for a user.
    - Validates user existence.
    - Enforces 1:1 (a user can own only one profile).
    - Enforces case-insensitive unique username.
    - Returns 201 Created with Location header.
    """
    _assert_user_exists(payload.user_id)
    _assert_user_has_no_profile(payload.user_id)

    if _username_exists(payload.username):
        raise HTTPException(status_code=400, detail="Username already exists")

    profile = ProfileRead(**payload.model_dump())
    profiles[profile.id] = profile
    profiles_by_user[profile.user_id] = profile.id
    
    # Set Location header per RFC 7231
    response.headers["Location"] = f"/profiles/{profile.id}"
    
    # Add HATEOAS links
    profile = _build_profile_with_links(profile)
    
    return profile


@app.get("/profiles", tags=["profiles"])
def list_profiles(
    user_id: Optional[UUID] = Query(None, description="Filter by owner user_id"),
    username: Optional[str] = Query(None, description="Filter by exact username (case-insensitive)"),
    pageSize: int = Query(10, ge=1, le=100, description="Number of items per page"),
    pageToken: Optional[str] = Query(None, description="Opaque pagination token")
):
    """
    List profiles with optional filters and pagination.
    Supports cursor-based pagination with opaque pageToken.
    """
    results = list(profiles.values())
    if user_id is not None:
        results = [p for p in results if p.user_id == user_id]
    if username is not None:
        u = username.lower()
        results = [p for p in results if p.username.lower() == u]
    
    # Add HATEOAS links to all profiles
    results = [_build_profile_with_links(p) for p in results]
    
    # Paginate results
    page_items, next_token = paginate(results, pageSize, pageToken)
    
    # Build response with pagination links
    return {
        "items": page_items,
        "pageSize": pageSize,
        "pageToken": pageToken,
        "_links": {
            "self": f"/profiles?pageSize={pageSize}" + (f"&pageToken={pageToken}" if pageToken else ""),
            "next": f"/profiles?pageSize={pageSize}&pageToken={next_token}" if next_token else None
        }
    }


@app.get("/profiles/{profile_id}", tags=["profiles"])
def get_profile(
    profile_id: UUID = Path(..., description="Profile ID (UUID)"),
    if_none_match: Optional[str] = Header(None, description="ETag from previous request")
):
    """
    Retrieve a single profile by ID.
    Supports conditional request with If-None-Match (ETag).
    Returns 304 Not Modified if ETag matches.
    """
    if profile_id not in profiles:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = profiles[profile_id]
    current_etag = etag_from_model(profile)
    
    # Check If-None-Match (RFC 7232)
    if should_return_304(if_none_match, current_etag):
        raise HTTPException(status_code=304, detail="Not Modified")
    
    # Add HATEOAS links
    profile = _build_profile_with_links(profile)
    
    # Return JSONResponse with ETag header
    return JSONResponse(
        status_code=200,
        content=profile.model_dump(mode='json'),
        headers={"ETag": current_etag, "Cache-Control": "max-age=3600"}
    )


@app.patch("/profiles/{profile_id}", tags=["profiles"])
def update_profile(
    profile_id: UUID,
    patch: ProfileUpdate,
    if_match: Optional[str] = Header(None, description="ETag for conditional update")
):
    """
    Partially update a profile.
    - Only applies provided fields (PATCH semantics).
    - If username is updated, enforce case-insensitive uniqueness.
    - If user_id were mutable (not recommended), we would re-enforce 1:1; but here user_id is immutable.
    - Supports conditional update with If-Match (ETag).
    """
    if profile_id not in profiles:
        raise HTTPException(status_code=404, detail="Profile not found")

    current_profile = profiles[profile_id]
    current_etag = etag_from_model(current_profile)
    
    # Check If-Match (RFC 7232)
    if not should_process_request(if_match, current_etag):
        raise HTTPException(status_code=412, detail="Precondition Failed")

    current = current_profile.model_dump()
    changes = patch.model_dump(exclude_unset=True)

    # Enforce username uniqueness if it is being changed
    new_username = changes.get("username")
    if new_username and _username_exists(new_username, exclude_id=profile_id):
        raise HTTPException(status_code=400, detail="Username already exists")

    current.update(changes)
    updated = ProfileRead(**current)
    profiles[profile_id] = updated
    
    # Add HATEOAS links
    updated = _build_profile_with_links(updated)
    
    # Return JSONResponse with new ETag header
    new_etag = etag_from_model(updated)
    return JSONResponse(
        status_code=200,
        content=updated.model_dump(mode='json'),
        headers={"ETag": new_etag}
    )


@app.delete("/profiles/{profile_id}", status_code=204, tags=["profiles"])
def delete_profile(profile_id: UUID):
    """
    Delete a profile and its user->profile mapping.
    """
    if profile_id not in profiles:
        raise HTTPException(status_code=404, detail="Profile not found")
    prof = profiles.pop(profile_id)
    profiles_by_user.pop(prof.user_id, None)
    return None
# -----------------------------------------------------------------------------
# Profile CRUD Endpoint
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Root
# -----------------------------------------------------------------------------
@app.get("/")
def root():
    return {"message": "Welcome to the User & Profile Service. See /docs for OpenAPI UI."}

# -----------------------------------------------------------------------------
# Entrypoint for `python main.py`
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
