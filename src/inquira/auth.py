from fastapi import APIRouter, HTTPException, Request, Depends, Response
from pydantic import BaseModel, Field
from typing import Optional
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from .database import (
    create_user, get_user_by_username, get_user_by_id,
    create_session, get_session, update_session, add_chat_message,
    migrate_json_to_sqlite, update_user_password, delete_user_account
)

router = APIRouter(tags=["Authentication"])

# Migrate existing JSON data to SQLite on startup
migrate_json_to_sqlite()

class UserRegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6)

class UserLoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6)

class UserResponse(BaseModel):
    user_id: str
    username: str
    created_at: str

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=6)
    new_password: str = Field(min_length=6)
    confirm_password: str = Field(min_length=6)

class DeleteAccountRequest(BaseModel):
    confirmation_text: str = Field(description="Must be 'DELETE' to confirm account deletion")
    current_password: str = Field(min_length=6, description="Current password for verification")

def hash_password(password: str, salt: str) -> str:
    """Hash password with salt using SHA-256"""
    return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()

def generate_salt() -> str:
    """Generate a random salt"""
    return secrets.token_hex(16)

def generate_session_token() -> str:
    """Generate a unique session token"""
    return str(uuid.uuid4())

def get_current_user(request: Request) -> dict:
    """Get current user from session cookie"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session_data = get_session(session_token)

    if not session_data:
        raise HTTPException(status_code=401, detail="Invalid session")

    # Check if session is expired (24 hours)
    session_created = datetime.fromisoformat(session_data["created_at"])
    if datetime.now() - session_created > timedelta(hours=24):
        raise HTTPException(status_code=401, detail="Session expired")

    user = get_user_by_id(session_data["user_id"])

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user

@router.post("/auth/register", response_model=UserResponse)
async def register_user(request: UserRegisterRequest):
    """Register a new user"""
    # Check if username already exists
    existing_user = get_user_by_username(request.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Create new user
    user_id = str(uuid.uuid4())
    salt = generate_salt()
    hashed_password = hash_password(request.password, salt)

    success = create_user(user_id, request.username, hashed_password, salt)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create user")

    return UserResponse(
        user_id=user_id,
        username=request.username,
        created_at=datetime.now().isoformat()
    )

@router.post("/auth/login")
async def login_user(request: UserLoginRequest, response: Response):
    """Login user and create session"""
    # Find user by username
    user = get_user_by_username(request.username)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Verify password using stored salt
    hashed_password = hash_password(request.password, user["salt"])
    if hashed_password != user["password_hash"]:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Create session
    session_token = generate_session_token()
    session_data = {
        "user_id": user["user_id"],
        "created_at": datetime.now().isoformat()
    }

    success = create_session(session_token, user["user_id"], session_data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create session")

    # Set session cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        max_age=86400,  # 24 hours
        samesite="lax"
    )

    return {"message": "Login successful", "user_id": user["user_id"]}

@router.post("/auth/logout")
async def logout_user(request: Request, response: Response):
    """Logout user by clearing session"""
    # For logout, we just clear the cookie since sessions are managed by the database
    # The session will naturally expire based on the timestamp
    response.delete_cookie("session_token")
    return {"message": "Logout successful"}

@router.get("/auth/verify")
async def verify_auth(current_user: dict = Depends(get_current_user)):
    """Verify if user is authenticated"""
    return {
        "authenticated": True,
        "user": {
            "user_id": current_user["user_id"],
            "username": current_user["username"]
        }
    }

@router.get("/auth/profile")
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """Get user profile"""
    return {
        "user_id": current_user["user_id"],
        "username": current_user["username"],
        "created_at": current_user["created_at"]
    }

@router.post("/auth/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """Change user password"""
    # Verify current password
    hashed_current = hash_password(request.current_password, current_user["salt"])
    if hashed_current != current_user["password_hash"]:
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Check if new password matches confirmation
    if request.new_password != request.confirm_password:
        raise HTTPException(status_code=400, detail="New password and confirmation do not match")

    # Generate new salt and hash for new password
    new_salt = generate_salt()
    new_hashed_password = hash_password(request.new_password, new_salt)

    # Update password in database
    success = update_user_password(current_user["user_id"], new_hashed_password, new_salt)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update password")

    return {"message": "Password changed successfully"}

@router.delete("/auth/delete-account")
async def delete_account(
    request: DeleteAccountRequest,
    response: Response,
    current_user: dict = Depends(get_current_user)
):
    """Delete user account permanently with confirmation"""
    # Verify confirmation text
    if request.confirmation_text != "DELETE":
        raise HTTPException(
            status_code=400,
            detail="Confirmation text must be exactly 'DELETE'"
        )

    # Verify current password
    hashed_current = hash_password(request.current_password, current_user["salt"])
    if hashed_current != current_user["password_hash"]:
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Delete the user account (this will CASCADE delete settings and sessions)
    success = delete_user_account(current_user["user_id"])
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete account")

    # Clear the session cookie
    if response:
        response.delete_cookie("session_token")

    return {"message": "Account deleted successfully"}