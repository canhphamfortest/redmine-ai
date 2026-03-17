#!/usr/bin/env python3
"""
Seed script to create default accounts and initial data
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, init_db
from app.auth import create_user, get_user_by_username
from app.models import User


def seed_default_accounts():
    """Create default user accounts"""
    db = SessionLocal()
    
    try:
        # Initialize database tables
        print("Initializing database tables...")
        init_db()
        
        # Default accounts to create
        default_accounts = [
            {
                "username": "admin",
                "password": "admin123",  # Should be changed in production!
                "email": "admin@example.com",
                "full_name": "Administrator",
                "is_admin": True
            },
            {
                "username": "user",
                "password": "user123",  # Should be changed in production!
                "email": "user@example.com",
                "full_name": "Regular User",
                "is_admin": False
            }
        ]
        
        print("\nCreating default accounts...")
        for account_data in default_accounts:
            username = account_data["username"]
            
            # Check if user already exists
            existing_user = get_user_by_username(db, username)
            if existing_user:
                print(f"  ⚠️  User '{username}' already exists, skipping...")
                continue
            
            # Create user
            user = create_user(
                db=db,
                username=account_data["username"],
                password=account_data["password"],
                email=account_data.get("email"),
                full_name=account_data.get("full_name"),
                is_admin=account_data.get("is_admin", False)
            )
            
            role = "Admin" if user.is_admin else "User"
            print(f"  ✅ Created {role}: {user.username} (email: {user.email})")
        
        print("\n✅ Default accounts seeded successfully!")
        print("\n⚠️  IMPORTANT: Change default passwords in production!")
        print("   Default credentials:")
        print("   - Admin: admin / admin123")
        print("   - User:  user / user123")
        
    except Exception as e:
        print(f"\n❌ Error seeding accounts: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_default_accounts()

