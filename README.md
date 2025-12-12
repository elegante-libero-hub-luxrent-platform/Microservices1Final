# User & Profile Service (Microservice 1) - Iteration 2

**Status**: ✅ **Complete & Tested**  
**Test Results**: 38/38 Postman Tests Pass | 8/8 Bash Script Tests Pass  
**Completion Date**: 2025-11-22

This service is part of a **luxury fashion rental platform**, responsible for **user accounts**, **membership levels**, and **public user profiles**.

---

## 📖 Complete Documentation

👉 **[See ITER2.md for full documentation](./ITER2.md)**

This file contains everything you need:
- ✅ Iteration 2 requirements (7 items)
- ✅ Feature implementations
- ✅ Quick start guide
- ✅ Test verification
- ✅ Usage examples
- ✅ Deployment instructions

---

## 🚀 Quick Start (3 Steps)

### Option 1: Development (Fastest - No Database)
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
# Visit http://localhost:8000/docs
```

### Option 2: Docker Compose (Recommended - With Database)
```bash
docker-compose up -d
# API: http://localhost:8000
# Database: MySQL running in container
```

### Option 3: Interactive Setup
```bash
bash quickstart.sh
# Select option 1, 2, or 3
```

---

## ✨ What's Implemented (Iter2)

| Feature | Status | Tests |
|---------|--------|-------|
| ETag (RFC 7232) | ✅ | 6/6 ✓ |
| Query Parameters | ✅ | 4/4 ✓ |
| Pagination | ✅ | 4/4 ✓ |
| 201 Created | ✅ | 4/4 ✓ |
| HATEOAS Links | ✅ | 2/2 ✓ |
| MySQL Database | ✅ | Running ✓ |
| Deployment | ✅ | Ready ✓ |

---

## 🧪 Test & Verify

```bash
# Run automated tests
bash test_api.sh
# Expected: 8/8 tests pass ✓

# Or use Postman
# Import: Postman_Tests_v2.json
# Expected: 38/38 tests pass ✓
```

---

## 📁 Project Structure

```
├── main.py                    # Dev version (in-memory)
├── main_db.py                 # Prod version (MySQL)
├── models/                    # Data models
├── services/                  # Business logic
├── utils/                     # ETag, pagination
├── deployment/                # Deploy scripts
├── Dockerfile                 # Container config
├── docker-compose.yml         # MySQL + API
├── test_api.sh               # Test script
├── quickstart.sh             # Setup wizard
└── ITER2.md                  # Full documentation ⭐
```

---

## 📚 More Information

- **Full Docs**: See [ITER2.md](./ITER2.md)
- **API Docs**: Visit http://localhost:8000/docs after starting
- **Examples**: Check ITER2.md for curl examples
- **Deployment**: See deployment section in ITER2.md

---

## 🔧 Tech Stack

- **Language**: Python 3.11
- **Framework**: FastAPI
- **Database**: MySQL 8.0 (with SQLAlchemy ORM)
- **Validation**: Pydantic v2
- **Container**: Docker & Docker Compose
- **Testing**: Postman + Bash scripts

---

**Ready to submit! 🎉**
