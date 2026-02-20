import sys
import os
from pathlib import Path

# Add src to python path so we can import modules
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parents[1]
sys.path.append(str(src_dir))

from app.api.auth import hash_password, generate_salt
from app.database.database import get_user_by_username, update_user_password, get_db_connection

def reset_password(username: str, new_password: str):
    """Reset password for a user"""
    print(f"Attempting to reset password for user: {username}")
    
    # Check if user exists
    user = get_user_by_username(username)
    if not user:
        print(f"❌ Error: User '{username}' not found.")
        return False
    
    user_id = user['user_id']
    print(f"Found user with ID: {user_id}")
    
    # Generate new credentials
    try:
        new_salt = generate_salt()
        new_hash = hash_password(new_password, new_salt)
        
        # Update in database
        success = update_user_password(user_id, new_hash, new_salt)
        
        if success:
            print(f"✅ Success: Password for '{username}' has been updated.")
            return True
        else:
            print("❌ Error: Failed to update password in database.")
            return False
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        return False

if __name__ == "__main__":
    if len(sys.path) < 2:
        print("Usage: python reset_password.py <username> [new_password]")
        sys.exit(1)
        
    import argparse
    parser = argparse.ArgumentParser(description="Reset user password")
    parser.add_argument("username", help="Username to reset password for")
    parser.add_argument("password", help="New password (optional, will prompt if not provided)", nargs="?")
    
    args = parser.parse_args()
    
    username = args.username
    password = args.password
    
    if not password:
        import getpass
        password = getpass.getpass(f"Enter new password for {username}: ")
        confirm = getpass.getpass(f"Confirm new password: ")
        
        if password != confirm:
            print("❌ Error: Passwords do not match.")
            sys.exit(1)
            
    if len(password) < 6:
        print("❌ Error: Password must be at least 6 characters long.")
        sys.exit(1)
        
    reset_password(username, password)
