"""
Database initialization and migration scripts.
Run this script to set up the MySQL database schema.

Usage:
    python schema.py  # Create all tables
"""

from database import engine, Base, init_db, drop_db
from models.orm import UserDB, ProfileDB


def create_schema():
    """Create all database tables."""
    print("Creating database schema...")
    init_db()
    print("✓ Database schema created successfully")
    print("\nTables created:")
    print("  - users")
    print("  - profiles")


def recreate_schema():
    """Drop and recreate all tables (WARNING: Destructive)."""
    print("WARNING: This will delete all data!")
    confirm = input("Are you sure? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Operation cancelled.")
        return
    
    print("Dropping all tables...")
    drop_db()
    print("✓ Tables dropped")
    
    print("Creating new tables...")
    init_db()
    print("✓ Database schema recreated")


def seed_sample_data():
    """Seed database with sample data for testing."""
    from database import SessionLocal
    from models.orm import UserDB, ProfileDB
    import uuid
    import json
    from datetime import datetime
    
    db = SessionLocal()
    try:
        # Check if data already exists
        if db.query(UserDB).count() > 0:
            print("Database already contains data. Skipping seed.")
            return
        
        # Create sample users
        user1_id = uuid.uuid4()
        user2_id = uuid.uuid4()
        
        user1 = UserDB(
            id=user1_id,
            name="Kobe Bryant",
            email="kobe24@example.com",
            phone="+11234567890",
            membership_tier="PRO",
            password_hash="hashed_password_123"  # In production, use proper hashing
        )
        
        user2 = UserDB(
            id=user2_id,
            name="LeBron James",
            email="lebron23@example.com",
            phone="+19876543210",
            membership_tier="PROMAX",
            password_hash="hashed_password_456"
        )
        
        db.add(user1)
        db.add(user2)
        db.commit()
        
        # Create sample profiles
        profile1 = ProfileDB(
            id=uuid.uuid4(),
            user_id=user1_id,
            username="mamba_24",
            display_name="Black Mamba",
            avatar_url="https://cdn.example.com/avatars/kobe.png",
            bio="Love hoops & craftsmanship.",
            style_tags=json.dumps(["street", "minimal"])
        )
        
        profile2 = ProfileDB(
            id=uuid.uuid4(),
            user_id=user2_id,
            username="king_james",
            display_name="King James",
            avatar_url="https://cdn.example.com/avatars/lebron.png",
            bio="Fashion forward.",
            style_tags=json.dumps(["luxury", "casual"])
        )
        
        db.add(profile1)
        db.add(profile2)
        db.commit()
        
        print("✓ Sample data seeded successfully")
        print(f"  - Created {db.query(UserDB).count()} users")
        print(f"  - Created {db.query(ProfileDB).count()} profiles")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Error seeding data: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "recreate":
        recreate_schema()
    elif len(sys.argv) > 1 and sys.argv[1] == "seed":
        create_schema()
        seed_sample_data()
    else:
        create_schema()
