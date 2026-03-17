#!/usr/bin/env python3
"""
Script to create an admin user from command line
Usage: python scripts/create_admin_user.py <username> <password> [email] [full_name]
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, init_db
from app.auth import create_user, get_user_by_username


def create_admin_user(username: str, password: str, email: str = None, full_name: str = None):
    """Create an admin user"""
    db = SessionLocal()
    
    try:
        # Initialize database tables
        init_db()
        
        # Check if user already exists
        existing_user = get_user_by_username(db, username)
        if existing_user:
            print(f"❌ User '{username}' already exists!")
            return False
        
        # Create admin user
        user = create_user(
            db=db,
            username=username,
            password=password,
            email=email or f"{username}@example.com",
            full_name=full_name or username,
            is_admin=True
        )
        
        print(f"✅ Admin user created successfully!")
        print(f"   Username: {user.username}")
        print(f"   Email: {user.email}")
        print(f"   Full Name: {user.full_name}")
        print(f"   Is Admin: {user.is_admin}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/create_admin_user.py <username> <password> [email] [full_name]")
        print("\nExample:")
        print("  python scripts/create_admin_user.py admin mypassword123")
        print("  python scripts/create_admin_user.py admin mypassword123 admin@example.com 'Admin User'")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    email = sys.argv[3] if len(sys.argv) > 3 else None
    full_name = sys.argv[4] if len(sys.argv) > 4 else None
    
    success = create_admin_user(username, password, email, full_name)
    sys.exit(0 if success else 1)

