"""
User & Profile Service API - Database-backed version
Microservice 1 for Iter2 (Cloud Compute deployment)

This version uses SQLAlchemy ORM with MySQL/SQLite persistence.
For in-memory version (development), use main.py instead.

Environment variables:
  DB_USER: MySQL username (default: ms1_user)
  DB_PASSWORD: MySQL password (default: password123)
  DB_HOST: MySQL host (default: localhost)
  DB_PORT: MySQL port (default: 3306)
  DB_NAME: Database name (default: ms1_db)
  USE_SQLITE: Use SQLite instead of MySQL (default: False)
  FASTAPIPORT: API port (default: 8000)
"""

from __future__ import annotations

import os
import logging
from typing import Dict, List, Optional
from uuid import UUID

# [新增] 引入 dotenv，让本地直接运行 python main_db.py 也能读到配置
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends, Query, Path, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from auth import router as auth_router, require_jwt
from sqlalchemy.orm import Session

from models.user import UserCreate, UserUpdate, UserRead
from models.profile import ProfileCreate, ProfileRead, ProfileUpdate
from models.orm import UserDB, ProfileDB
# [修改] 引入额外的变量用于日志显示
from database import get_db, init_db, SessionLocal, INSTANCE_CONNECTION_NAME, DB_HOST, DB_NAME
from services.database import UserService, ProfileService
from utils.etag import generate_etag, etag_from_model, should_return_304, should_process_request
from utils.pagination import paginate, PaginationParams

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# [修改] Cloud Run 强制要求监听 PORT 环境变量 (8080)，本地没有 PORT 则回退到 8000
port = int(os.environ.get("PORT", 8000))

app = FastAPI(
    title="Person/Address API (Database-backed)",
    description="User & Profile Service with MySQL persistence",
    version="0.2.0-db",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"], 
)

# Session middleware 是 Authlib 做 OAuth2 登录所必须的
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET_KEY", "dev-session-secret"),
)

# 挂载共享的 auth 路由 (/auth/login, /auth/callback)
app.include_router(auth_router)


# Helper functions for HATEOAS links
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


# ============================================================================
# Users CRUD Endpoints
# ============================================================================

@app.post("/users", response_model=UserRead, status_code=201, tags=["users"])
def create_user(
    payload: UserCreate,
    response: JSONResponse,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_jwt),
):
    """
    Create a new user.
    - Enforces email and phone uniqueness.
    - Returns 201 Created with Location header.
    """
    # Check uniqueness
    if UserService.user_exists_by_email(db, payload.email):
        raise HTTPException(status_code=400, detail="Email already exists")
    if UserService.user_exists_by_phone(db, payload.phone):
        raise HTTPException(status_code=400, detail="Phone already exists")
    
    # Create user
    user = UserService.create_user(db, payload)
    
    # Add HATEOAS links
    user = _build_user_with_links(user)
    
    # Set Location header
    return JSONResponse(
        status_code=201,
        content=user.model_dump(mode='json', by_alias=True),
        headers={"Location": f"/users/{user.id}"}
    )


@app.get("/users", tags=["users"])
def list_users(
    name: Optional[str] = Query(None, description="Filter by exact name"),
    email: Optional[str] = Query(None, description="Filter by exact email"),
    phone: Optional[str] = Query(None, description="Filter by exact phone"),
    membership_tier: Optional[str] = Query(None, description="Filter by tier"),
    pageSize: int = Query(10, ge=1, le=100, description="Items per page"),
    pageToken: Optional[str] = Query(None, description="Pagination token"),
    db: Session = Depends(get_db)
):
    """
    List users with optional filters and pagination.
    """
    # Decode pagination
    params = PaginationParams(pageSize, pageToken)
    offset = params.offset
    
    # Query with filters
    users, total = UserService.list_users(
        db,
        name=name,
        email=email,
        phone=phone,
        membership_tier=membership_tier,
        offset=offset,
        limit=pageSize
    )
    
    # Add HATEOAS links
    users = [_build_user_with_links(u) for u in users]
    
    # Build pagination response
    has_next = (offset + pageSize) < total
    next_token = None
    if has_next:
        next_token = PaginationParams.encode_page_token(offset + pageSize)
    
    return {
        "items": users,
        "pageSize": pageSize,
        "pageToken": pageToken,
        "total": total,
        "_links": {
            "self": f"/users?pageSize={pageSize}" + (f"&pageToken={pageToken}" if pageToken else ""),
            "next": f"/users?pageSize={pageSize}&pageToken={next_token}" if next_token else None
        }
    }


@app.get("/users/{user_id}", tags=["users"])
def get_user(
    user_id: UUID = Path(..., description="User ID"),
    if_none_match: Optional[str] = Header(None, description="ETag"),
    db: Session = Depends(get_db)
):
    """
    Retrieve a single user by ID.
    Supports conditional requests with If-None-Match (ETag).
    """
    user = UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    current_etag = etag_from_model(user)
    
    # Check If-None-Match
    if should_return_304(if_none_match, current_etag):
        raise HTTPException(status_code=304, detail="Not Modified")
    
    # Add HATEOAS links
    user = _build_user_with_links(user)
    
    return JSONResponse(
        status_code=200,
        content=user.model_dump(mode='json', by_alias=True),
        headers={"ETag": current_etag, "Cache-Control": "max-age=3600"}
    )


@app.patch("/users/{user_id}", tags=["users"])
def update_user(
    user_id: UUID,
    patch: UserUpdate,
    if_match: Optional[str] = Header(None, description="ETag"),
    db: Session = Depends(get_db)
):
    """
    Partially update a user with ETag support.
    """
    user = UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    current_etag = etag_from_model(user)
    
    # Check If-Match
    if not should_process_request(if_match, current_etag):
        raise HTTPException(status_code=412, detail="Precondition Failed")
    
    # Check uniqueness of new email/phone
    if patch.email and UserService.user_exists_by_email(db, patch.email, exclude_id=user_id):
        raise HTTPException(status_code=400, detail="Email already exists")
    if patch.phone and UserService.user_exists_by_phone(db, patch.phone, exclude_id=user_id):
        raise HTTPException(status_code=400, detail="Phone already exists")
    
    # Update
    user = UserService.update_user(db, user_id, patch)
    user = _build_user_with_links(user)
    
    new_etag = etag_from_model(user)
    return JSONResponse(
        status_code=200,
        content=user.model_dump(mode='json', by_alias=True),
        headers={"ETag": new_etag}
    )


@app.delete("/users/{user_id}", status_code=204, tags=["users"])
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_jwt),
):
    """Delete a user."""
    success = UserService.delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return None


# ============================================================================
# Profiles CRUD Endpoints
# ============================================================================

@app.post("/profiles", response_model=ProfileRead, status_code=201, tags=["profiles"])
def create_profile(payload: ProfileCreate, db: Session = Depends(get_db)):
    """
    Create a profile for a user.
    - Validates user existence.
    - Enforces 1:1 relationship (one profile per user).
    - Enforces unique username.
    """
    # Check user exists
    user = UserService.get_user(db, payload.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="User does not exist")
    
    # Check 1:1
    if ProfileService.profile_exists_for_user(db, payload.user_id):
        raise HTTPException(status_code=400, detail="User already has a profile")
    
    # Check username uniqueness
    if ProfileService.username_exists(db, payload.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Create profile
    profile = ProfileService.create_profile(db, payload)
    profile = _build_profile_with_links(profile)
    
    return JSONResponse(
        status_code=201,
        content=profile.model_dump(mode='json', by_alias=True),
        headers={"Location": f"/profiles/{profile.id}"}
    )


@app.get("/profiles", tags=["profiles"])
def list_profiles(
    user_id: Optional[UUID] = Query(None, description="Filter by owner user_id"),
    username: Optional[str] = Query(None, description="Filter by username"),
    pageSize: int = Query(10, ge=1, le=100, description="Items per page"),
    pageToken: Optional[str] = Query(None, description="Pagination token"),
    db: Session = Depends(get_db)
):
    """
    List profiles with optional filters and pagination.
    """
    # Decode pagination
    params = PaginationParams(pageSize, pageToken)
    offset = params.offset
    
    # Query with filters
    profiles, total = ProfileService.list_profiles(
        db,
        user_id=user_id,
        username=username,
        offset=offset,
        limit=pageSize
    )
    
    # Add HATEOAS links
    profiles = [_build_profile_with_links(p) for p in profiles]
    
    # Build pagination response
    has_next = (offset + pageSize) < total
    next_token = None
    if has_next:
        next_token = PaginationParams.encode_page_token(offset + pageSize)
    
    return {
        "items": profiles,
        "pageSize": pageSize,
        "pageToken": pageToken,
        "total": total,
        "_links": {
            "self": f"/profiles?pageSize={pageSize}" + (f"&pageToken={pageToken}" if pageToken else ""),
            "next": f"/profiles?pageSize={pageSize}&pageToken={next_token}" if next_token else None
        }
    }


@app.get("/profiles/{profile_id}", tags=["profiles"])
def get_profile(
    profile_id: UUID = Path(..., description="Profile ID"),
    if_none_match: Optional[str] = Header(None, description="ETag"),
    db: Session = Depends(get_db)
):
    """
    Retrieve a profile by ID with ETag support.
    """
    profile = ProfileService.get_profile(db, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    current_etag = etag_from_model(profile)
    
    # Check If-None-Match
    if should_return_304(if_none_match, current_etag):
        raise HTTPException(status_code=304, detail="Not Modified")
    
    # Add HATEOAS links
    profile = _build_profile_with_links(profile)
    
    return JSONResponse(
        status_code=200,
        content=profile.model_dump(mode='json', by_alias=True),
        headers={"ETag": current_etag, "Cache-Control": "max-age=3600"}
    )


@app.patch("/profiles/{profile_id}", tags=["profiles"])
def update_profile(
    profile_id: UUID,
    patch: ProfileUpdate,
    if_match: Optional[str] = Header(None, description="ETag"),
    db: Session = Depends(get_db)
):
    """
    Partially update a profile with ETag support.
    """
    profile = ProfileService.get_profile(db, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    current_etag = etag_from_model(profile)
    
    # Check If-Match
    if not should_process_request(if_match, current_etag):
        raise HTTPException(status_code=412, detail="Precondition Failed")
    
    # Check username uniqueness if being updated
    if patch.username and ProfileService.username_exists(db, patch.username, exclude_id=profile_id):
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Update
    profile = ProfileService.update_profile(db, profile_id, patch)
    profile = _build_profile_with_links(profile)
    
    new_etag = etag_from_model(profile)
    return JSONResponse(
        status_code=200,
        content=profile.model_dump(mode='json', by_alias=True),
        headers={"ETag": new_etag}
    )


@app.delete("/profiles/{profile_id}", status_code=204, tags=["profiles"])
def delete_profile(profile_id: UUID, db: Session = Depends(get_db)):
    """Delete a profile."""
    success = ProfileService.delete_profile(db, profile_id)
    if not success:
        raise HTTPException(status_code=404, detail="Profile not found")
    return None


# ============================================================================
# Livenessandhealth checks
# ============================================================================

@app.get("/")
def root():
    """Root endpoint with API info."""
    return {
        "message": "Welcome to User & Profile Service (Database-backed)",
        "version": "0.2.0-db",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint."""
    try:
        # Test database connection
        db.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": f"error: {str(e)}"}


# ============================================================================
# Startup and shutdown events
# ============================================================================

@app.on_event("startup")
def startup_event():
    """Initialize database on startup."""
    logger.info("=" * 60)
    logger.info("🚀 Starting User & Profile Service")
    
    # [关键修改] 智能打印日志，显示真实的连接方式 (Socket 还是 IP)
    if INSTANCE_CONNECTION_NAME:
        logger.info(f"🔗 Mode: Cloud Run (Unix Socket)")
        logger.info(f"🔌 Connection Name: {INSTANCE_CONNECTION_NAME}")
    else:
        logger.info(f"🔗 Mode: Local / TCP")
        logger.info(f"🔌 Host: {DB_HOST}")
    
    logger.info(f"📦 Database: {DB_NAME}")
    logger.info(f"🚪 API Port: {port}")
    logger.info("=" * 60)
    
    try:
        init_db()
        logger.info("✓ Database schema initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize database: {e}")
        # 在 Cloud Run 环境下，如果连不上数据库，通常建议直接崩溃，
        # 这样 Cloud Run 会知道启动失败，而不是带着错误的连接继续运行。
        raise


# ============================================================================
# Entry point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main_db:app",
        host="127.0.0.1",
        port=8000,   # 或者 8001，防止跟 main.py 撞端口
        reload=True,
    )
