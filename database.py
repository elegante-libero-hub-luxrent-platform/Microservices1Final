"""
Database configuration and session management for SQLAlchemy.
Supports in-memory SQLite (testing), MySQL (production), and GCP Secret Manager.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import logging
from google.cloud import secretmanager
from dotenv import load_dotenv

# Load .env for local development
load_dotenv()

logger = logging.getLogger(__name__)

Base = declarative_base()

# ==============================================================================
# 1. Helper: Fetch Secret from Google Cloud
# ==============================================================================
def get_secret(secret_name: str):
    """
    Fetch database password from GCP Secret Manager.
    """
    project_id = os.environ.get("GCP_PROJECT_ID")
    if not project_id or not secret_name:
        return None

    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.error(f"Failed to fetch secret '{secret_name}': {e}")
        return None

# ==============================================================================
# 2. Database Configuration
# ==============================================================================

# Basic Config (Environment Variables)
DB_USER = os.environ.get("CATALOG_DB_USER", os.environ.get("DB_USER", "ms1_user"))
DB_NAME = os.environ.get("CATALOG_DB_NAME", os.environ.get("DB_NAME", "ms1_db"))

# For Local / TCP connection
DB_HOST = os.environ.get("CATALOG_DB_HOST", os.environ.get("DB_HOST", "localhost"))
DB_PORT = os.environ.get("CATALOG_DB_PORT", os.environ.get("DB_PORT", "3306"))

# [New] For Cloud Run (Unix Socket) connection
# 如果队友设置了这个变量，我们就用 Socket 连，不再用 IP
INSTANCE_CONNECTION_NAME = os.environ.get("INSTANCE_CONNECTION_NAME")

# Password Logic
secret_name = os.environ.get("DB_PASSWORD_SECRET")
raw_password = os.environ.get("CATALOG_DB_PASSWORD", os.environ.get("DB_PASSWORD"))
DB_PASSWORD = "password123"

if secret_name:
    fetched = get_secret(secret_name)
    if fetched:
        DB_PASSWORD = fetched
        logger.info("Successfully loaded password from Secret Manager.")
elif raw_password:
    DB_PASSWORD = raw_password

# SQLite Toggle
USE_SQLITE = os.environ.get("USE_SQLITE", "False").lower() == "true"

# ==============================================================================
# 3. Create Engine (Smart Switch)
# ==============================================================================

if USE_SQLITE:
    DATABASE_URL = "sqlite:///:memory:"
    logger.info("Using SQLite in-memory database")
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

else:
    # Decide connection method: Socket (Cloud Run) vs TCP (Local)
    if INSTANCE_CONNECTION_NAME:
        # [Cloud Run Mode] Use Unix Socket
        # Format: mysql+pymysql://user:pass@/dbname?unix_socket=/cloudsql/INSTANCE_NAME
        socket_path = f"/cloudsql/{INSTANCE_CONNECTION_NAME}"
        DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@/{DB_NAME}?unix_socket={socket_path}"
        logger.info(f"🔌 Connecting via Unix Socket: {socket_path}")
    else:
        # [Local Mode] Use TCP IP
        DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        logger.info(f"🔌 Connecting via TCP: {DB_HOST}:{DB_PORT}")

    # Create Engine with production settings
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=5,
        max_overflow=10,
        connect_args={"connect_timeout": 10} # Fixed parameter name
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def init_db():
    Base.metadata.create_all(bind=engine)

def drop_db():
    Base.metadata.drop_all(bind=engine)
    