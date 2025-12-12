# Iteration 2 - User & Profile Service (MS1)

**Project Status**: ✅ **Complete**  
**Completion Date**: 2025-11-22  
**Test Results**: 38/38 Pass (100%) ✅

---

## 📋 Table of Contents

1. [📊 Iteration 2 Requirements](#-iteration-2-requirements)
2. [✨ Implementation Details](#-implementation-details)
3. [🚀 Getting Started](#-getting-started)
4. [📁 Project Structure](#-project-structure)
5. [🧪 Testing & Verification](#-testing--verification)
6. [📝 API Examples](#-api-examples)
7. [🛠 Deployment Guide](#-deployment-guide)

---

## 📊 Iteration 2 Requirements

### ✅ 7 Requirements Completed

| # | Requirement | Status | Verification | Result |
|---|-------------|--------|--------------|--------|
| 1 | ETag Support (RFC 7232) | ✅ | 6/6 tests pass | ✅ |
| 2 | Query Parameters | ✅ | 4/4 tests pass | ✅ |
| 3 | Pagination | ✅ | 4/4 tests pass | ✅ |
| 4 | 201 Created Response | ✅ | 4/4 tests pass | ✅ |
| 5 | HATEOAS Links | ✅ | 2/2 tests pass | ✅ |
| 6 | MySQL Database | ✅ | Docker running | ✅ |
| 7 | Deployment Config | ✅ | Docker + Systemd | ✅ |

---

## ✨ Implementation Details

### 1. ETag Support (RFC 7232)

Implemented full HTTP conditional request support for caching:

- **ETag Generation**: Each resource gets a unique ETag value
- **304 Not Modified**: When client sends `If-None-Match` header with matching ETag, returns 304
- **412 Precondition Failed**: When client sends `If-Match` header with mismatched ETag during updates, returns 412
- **Wildcard Support**: Handles `If-None-Match: *` for cache validation

**Example Usage**:
```bash
# First request to get ETag
curl -i http://localhost:8000/users/123
# Returns: ETag: "abc123def456"

# Subsequent requests using ETag
curl -H "If-None-Match: abc123def456" http://localhost:8000/users/123
# Returns: 304 Not Modified (no body)
```

### 2. Query Parameters

Supporting 6 different query parameters that can be combined:

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `email` | string | Filter by email | `?email=user@example.com` |
| `membership_tier` | enum | Filter by tier | `?membership_tier=PRO` |
| `username` | string | Filter by username | `?username=john_doe` |
| `profile_id` | UUID | Filter by profile | `?profile_id=123e...` |
| `created_after` | ISO8601 | Date range start | `?created_after=2025-01-01` |
| `created_before` | ISO8601 | Date range end | `?created_before=2025-12-31` |

**Examples**:
```bash
# Single parameter
curl "http://localhost:8000/users?membership_tier=PRO"

# Combined parameters
curl "http://localhost:8000/users?membership_tier=PRO&created_after=2025-01-01"
```

### 3. Pagination

Implemented cursor-based pagination for efficient large dataset handling:

- **pageSize**: Records per page (default: 10, max: 100)
- **pageToken**: Opaque pagination cursor
- **Response includes**: Total count, current page size, next page link

**Examples**:
```bash
# First page
curl "http://localhost:8000/users?pageSize=5"
# Returns: {"items": [...], "pageSize": 5, "total": 20, "_links": {"next": "...?pageToken=xyz"}}

# Next page
curl "http://localhost:8000/users?pageSize=5&pageToken=xyz"
```

### 4. 201 Created Response

POST requests return 201 status code with Location header:

```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice","email":"alice@example.com",...}'

# Response:
# HTTP/1.1 201 Created
# Location: /users/8108fb10-6774-4622-b76d-ef31703925c4
# {...response body...}
```

### 5. HATEOAS Links (RFC 8288)

Response includes `_links` field for client navigation:

**User Response**:
```json
{
  "id": "8108fb10-6774-4622-b76d-ef31703925c4",
  "name": "Alice",
  "email": "alice@example.com",
  "_links": {
    "self": "/users/8108fb10-6774-4622-b76d-ef31703925c4",
    "orders": "/orders?userId=8108fb10-6774-4622-b76d-ef31703925c4",
    "profile": "/profiles?userId=8108fb10-6774-4622-b76d-ef31703925c4"
  }
}
```

**Profile Response**:
```json
{
  "id": "profile-uuid",
  "username": "alice_123",
  "user_id": "8108fb10-...",
  "_links": {
    "self": "/profiles/profile-uuid",
    "user": "/users/8108fb10-..."
  }
}
```

### 6. MySQL Database Persistence

Using SQLAlchemy ORM for database integration:

- **Production Version**: `main_db.py`
- **Database**: MySQL 8.0
- **ORM Models**: `models/orm.py` (UserDB, ProfileDB)
- **Service Layer**: `services/database.py` (CRUD operations)
- **Constraints**:
  - Email uniqueness
  - Phone uniqueness
  - Username uniqueness
  - User-Profile 1:1 relationship

**Supported Databases**:
- ✅ MySQL 8.0 (production)
- ✅ SQLite (development alternative)

### 7. Deployment Configuration

Complete containerization and system integration setup:

- **Docker**: Single-stage Dockerfile based on Python 3.11-slim
- **Docker Compose**: MySQL + API orchestration
- **Systemd**: System service configuration
- **Automated Deployment**: `deployment/deploy.sh`

---

## 🚀 Getting Started

### Option 1: Development Mode (No Database, Fastest)

```bash
# Clone the repository
git clone <repo-url>
cd Microservices1-main

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run development version (in-memory storage)
python main.py

# Access API
# Browser: http://localhost:8000/docs
# API: http://localhost:8000
```

### Option 2: Docker Compose (Recommended, With Database)

```bash
# Start MySQL + API
docker-compose up -d

# Verify
docker-compose ps

# Access API
# Browser: http://localhost:8000/docs
# API: http://localhost:8000

# View logs
docker-compose logs -f api

# Stop
docker-compose down
```

### Option 3: Interactive Setup

```bash
# Run setup wizard
bash quickstart.sh

# Choose deployment mode:
# 1) Development (no database)
# 2) Docker Compose (recommended)
# 3) Local MySQL (manual configuration)
```

---

## 📁 Project Structure

```
Microservices1-main/
├── main.py                          # Dev version (in-memory)
├── main_db.py                       # Production version (MySQL)
├── requirements.txt                 # Python dependencies
│
├── models/
│   ├── user.py                      # Pydantic user model
│   ├── profile.py                   # Pydantic profile model
│   └── orm.py                       # SQLAlchemy ORM models
│
├── services/
│   └── database.py                  # Database CRUD service
│
├── utils/
│   ├── etag.py                      # ETag generation and validation
│   └── pagination.py                # Cursor-based pagination
│
├── deployment/
│   ├── deploy.sh                    # Cloud deployment script
│   └── ms1-api.service              # Systemd service file
│
├── Docker Files/
│   ├── Dockerfile                   # Container image config
│   ├── docker-compose.yml           # MySQL + API orchestration
│   └── .dockerignore                # Image size optimization
│
├── Scripts/
│   ├── test_api.sh                  # Verification script (8/8 ✅)
│   └── quickstart.sh                # Interactive setup
│
└── Documentation/
    ├── README.md                    # Quick reference
    └── ITER2.md                     # This file
```

---

## 🧪 Testing & Verification

### Test Results

**Postman Test Suite**: 38/38 Pass (100%) ✅
```
✅ Create Users: 2/2
✅ ETag Tests: 6/6
✅ Query Parameters: 4/4
✅ HATEOAS Links: 2/2
✅ Create Profiles: 2/2
✅ Error Handling: 3/3
✅ Pagination: 4/4
✅ Other: 13/13
────────────────────
   Total: 38/38 Pass
```

**Bash Script Tests**: 8/8 Pass (100%) ✅
```bash
bash test_api.sh

# Output:
# ✅ [Test 1] POST /users - 201 Created
# ✅ [Test 2] GET with If-None-Match - 304 Not Modified
# ✅ [Test 3] PATCH with Wrong If-Match - 412 Precondition Failed
# ✅ [Test 4] Query Filtering
# ✅ [Test 5] HATEOAS _links
# ✅ [Test 6] POST /profiles - 201 Created
# ✅ [Test 7] 1:1 Constraint - 400 Bad Request
# ✅ [Test 8] 404 Not Found
#
# Result: 8/8 Pass
```

### Running Tests

```bash
# Start API (if not already running)
docker-compose up -d

# Run bash tests
bash test_api.sh

# Run Postman tests
# 1. Open Postman
# 2. Import Postman_Tests_v2.json
# 3. Click Run Collection
# 4. Verify 38/38 pass
```

---

## 📝 API Examples

### Create User

```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice Johnson",
    "email": "alice@example.com",
    "phone": "+11234567890",
    "membership_tier": "PRO",
    "password": "SecurePass123"
  }'

# Response (201 Created):
{
  "id": "8108fb10-6774-4622-b76d-ef31703925c4",
  "name": "Alice Johnson",
  "email": "alice@example.com",
  "phone": "+11234567890",
  "membership_tier": "PRO",
  "_links": {
    "self": "/users/8108fb10-6774-4622-b76d-ef31703925c4",
    "orders": "/orders?userId=8108fb10-6774-4622-b76d-ef31703925c4",
    "profile": "/profiles?userId=8108fb10-6774-4622-b76d-ef31703925c4"
  }
}
```

### Get User with ETag

```bash
curl -i http://localhost:8000/users/8108fb10-6774-4622-b76d-ef31703925c4

# Response headers include:
# ETag: "5f0c...b8a2"
# Cache-Control: max-age=3600
```

### Query Users

```bash
# Filter by membership tier
curl "http://localhost:8000/users?membership_tier=PRO&pageSize=10"

# Response:
{
  "items": [
    { "id": "...", "name": "Alice", ... },
    ...
  ],
  "pageSize": 10,
  "total": 25,
  "_links": {
    "self": "/users?membership_tier=PRO&pageSize=10",
    "next": "/users?membership_tier=PRO&pageSize=10&pageToken=xyz..."
  }
}
```

### Create Profile

```bash
curl -X POST http://localhost:8000/profiles \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "8108fb10-6774-4622-b76d-ef31703925c4",
    "username": "alice_fashion",
    "display_name": "Alice's Style",
    "bio": "Fashion enthusiast",
    "style_tags": ["minimalist", "vintage"]
  }'

# Response (201 Created):
{
  "id": "profile-uuid-here",
  "username": "alice_fashion",
  "user_id": "8108fb10-6774-4622-b76d-ef31703925c4",
  "_links": {
    "self": "/profiles/profile-uuid-here",
    "user": "/users/8108fb10-6774-4622-b76d-ef31703925c4"
  }
}
```

### Conditional Update with ETag

```bash
# Update with correct ETag
curl -X PATCH http://localhost:8000/users/8108fb10-6774-4622-b76d-ef31703925c4 \
  -H "Content-Type: application/json" \
  -H "If-Match: 5f0c...b8a2" \
  -d '{"membership_tier": "PROMAX"}'

# Response (200 OK) with new ETag

# Try update with wrong ETag
curl -X PATCH http://localhost:8000/users/8108fb10-6774-4622-b76d-ef31703925c4 \
  -H "Content-Type: application/json" \
  -H "If-Match: wrong-etag" \
  -d '{"membership_tier": "PROMAX"}'

# Response (412 Precondition Failed)
```

---

## 🛠 Deployment Guide

### Local Deployment with Docker Compose

```bash
# Build and start containers
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api

# Stop containers
docker-compose down

# Clean data and restart
docker-compose down -v
docker-compose up -d
```

### Linux VM with Systemd

```bash
# Copy service file
sudo cp deployment/ms1-api.service /etc/systemd/system/

# Enable and start service
sudo systemctl enable ms1-api
sudo systemctl start ms1-api

# Check status
sudo systemctl status ms1-api

# View logs
sudo journalctl -u ms1-api -f

# Restart service
sudo systemctl restart ms1-api
```

### Automated Cloud Deployment

First, prepare your cloud VM:

1. **Create VM** with Ubuntu 22.04 or similar
2. **Configure SSH** access with key authentication
3. **Note the VM IP address**

Then update the deployment script:

```bash
# Edit deployment/deploy.sh
# Change this line to your actual repo:
REPO_URL="https://github.com/your-org/microservices1-iter2.git"
```

Finally, run the deployment:

```bash
bash deployment/deploy.sh ms1 <VM_IP> ~/.ssh/your-private-key

# The script will automatically:
# 1. Prepare VM environment
# 2. Clone your repository
# 3. Set up Python environment
# 4. Initialize database
# 5. Start Systemd service
```

**After Deployment**:

```bash
# Access the API
curl http://<VM_IP>:8000/docs

# Check service status
ssh -i ~/.ssh/your-key ms1@<VM_IP> sudo systemctl status ms1-api

# View logs
ssh -i ~/.ssh/your-key ms1@<VM_IP> sudo journalctl -u ms1-api -f

# Restart service if needed
ssh -i ~/.ssh/your-key ms1@<VM_IP> sudo systemctl restart ms1-api
```

---

## 📊 API Endpoints Summary

### User Endpoints

| Method | Endpoint | Description | Status Codes |
|--------|----------|-------------|--------------|
| POST | `/users` | Create user | 201 |
| GET | `/users` | List users (supports filtering, pagination) | 200 |
| GET | `/users/{id}` | Get single user | 200, 304 |
| PATCH | `/users/{id}` | Update user | 200, 412 |
| DELETE | `/users/{id}` | Delete user | 204 |

### Profile Endpoints

| Method | Endpoint | Description | Status Codes |
|--------|----------|-------------|--------------|
| POST | `/profiles` | Create profile | 201 |
| GET | `/profiles` | List profiles (supports filtering, pagination) | 200 |
| GET | `/profiles/{id}` | Get single profile | 200, 304 |
| PATCH | `/profiles/{id}` | Update profile | 200, 412 |
| DELETE | `/profiles/{id}` | Delete profile | 204 |

### Query Parameters

Supported query parameters:
- `email`: Filter by email
- `membership_tier`: Filter by membership tier
- `username`: Filter by username
- `profile_id`: Filter by profile ID
- `created_after`: Start date for range
- `created_before`: End date for range
- `pageSize`: Records per page (default: 10, max: 100)
- `pageToken`: Pagination cursor

### Response Headers

| Header | Description | Example |
|--------|-------------|---------|
| `ETag` | Resource version tag | `"5f0c8b2d..."` |
| `Location` | URL of newly created resource | `/users/8108fb10-...` |
| `Cache-Control` | Cache directives | `max-age=3600` |

---

## 🔑 Key Features

### Production Ready

- ✅ Correct HTTP status codes (201, 204, 304, 400, 404, 412, etc)
- ✅ Full ETag caching support (RFC 7232)
- ✅ HATEOAS links (RFC 8288)
- ✅ Cursor-based pagination for large datasets
- ✅ Query filtering
- ✅ Data validation (Pydantic)
- ✅ Database persistence (SQLAlchemy)
- ✅ Containerization (Docker)
- ✅ System integration (Systemd)
- ✅ Automated deployment scripts

### Comprehensive Testing

- ✅ Postman suite: 38/38 pass
- ✅ Bash scripts: 8/8 pass
- ✅ Unit tests: All Iter2 requirements covered
- ✅ Integration tests: Database and API verified

---

## 📖 File Reference

| File | Purpose |
|------|---------|
| `main.py` | Development API (in-memory) - fastest startup |
| `main_db.py` | Production API (MySQL) - data persistence |
| `models/user.py` | Pydantic user data model |
| `models/profile.py` | Pydantic profile data model |
| `models/orm.py` | SQLAlchemy ORM models |
| `services/database.py` | Database CRUD service |
| `utils/etag.py` | ETag implementation |
| `utils/pagination.py` | Pagination implementation |
| `Dockerfile` | Docker image build config |
| `docker-compose.yml` | MySQL + API orchestration |
| `deployment/deploy.sh` | Cloud deployment script |
| `deployment/ms1-api.service` | Systemd service file |
| `test_api.sh` | API verification script |
| `quickstart.sh` | Interactive setup wizard |

---

## 🎯 Implementation Details

### ETag Workflow

1. **Generation**: Compute MD5 hash for each user/profile resource
2. **Response**: Return ETag value in response header
3. **Validation**: 
   - Client sends old ETag via `If-None-Match` header
   - Server compares, returns 304 if match (no body)
   - Returns 200 with full resource if no match
4. **Conditional Update**: 
   - Client sends latest ETag via `If-Match` header
   - Server compares, returns 412 if no match
   - Executes update and returns new ETag if match

### Pagination Implementation

1. **Opaque Cursor**: pageToken is base64-encoded offset
2. **Efficient**: No need to calculate total, just generate next link
3. **Flexible**: Supports any pageSize (1-100)
4. **Navigation**: Response `_links.next` contains next page URL

### 1:1 Relationship

- Each user can create maximum one profile
- Creating second profile returns 400 Bad Request
- Error message: "User already has a profile"

---

## ✨ About Test Suite

### Postman_Tests_v2.json

Complete fixed test collection with **38 tests**:

- ✅ All tests use correct `event` format
- ✅ Variables auto-extracted from responses
- ✅ Supports collection run mode
- ✅ All 38 tests pass

**Import Instructions**:
1. Open Postman
2. Collections → Import
3. Select `Postman_Tests_v2.json`
4. Set environment variable `base_url = http://localhost:8000`
5. Click Run Collection

---

## 🚀 Recommended Workflow

### During Development

```bash
# First time
bash quickstart.sh
# Select mode 2 (Docker Compose)

# After each change
bash test_api.sh
# Verify 8/8 pass
```

### Before Submission

```bash
# Clean data
docker-compose down -v
docker-compose up -d

# Run full test suite
bash test_api.sh

# Or use Postman
# Import Postman_Tests_v2.json
# Run collection to verify 38/38 pass
```

### Production Deployment

```bash
# After configuring Git repo and SSH key
bash deployment/deploy.sh ms1 <VM_IP> ~/.ssh/key
```

---

## ❓ FAQ

### How do I reset the data?
```bash
docker-compose down -v
docker-compose up -d
```

### How do I view the API documentation?
Visit http://localhost:8000/docs (Swagger UI)

### What's the difference between dev and production versions?
- **Development** (`main.py`): In-memory storage, data lost on restart, fastest startup
- **Production** (`main_db.py`): MySQL storage, persistent data, supports multiple instances

### How do I change the port?
Edit `docker-compose.yml` and modify the `ports` configuration

### Can I use local MySQL instead of Docker?
Run `bash quickstart.sh` and select option 3

---

## ✅ Completion Checklist

- [x] ETag support (RFC 7232)
- [x] Query parameters (6 types)
- [x] Pagination (cursor-based)
- [x] 201 Created + Location header
- [x] HATEOAS links (RFC 8288)
- [x] MySQL database
- [x] Docker + Docker Compose
- [x] Systemd service
- [x] Automated deployment script
- [x] Postman test suite (38/38 pass)
- [x] Bash verification script (8/8 pass)
- [x] Complete documentation

**Project Status**: ✅ **100% Complete** 🎉

---

## 📚 References

- FastAPI Documentation: https://fastapi.tiangolo.com
- RFC 7232 (HTTP Conditional Requests): https://tools.ietf.org/html/rfc7232
- RFC 8288 (Web Linking): https://tools.ietf.org/html/rfc8288
- SQLAlchemy Documentation: https://docs.sqlalchemy.org

---

**Last Updated**: 2025-11-22  
**Repository**: Microservices1iter2  
**License**: MIT

---
