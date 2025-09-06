from fastapi import APIRouter, HTTPException, Depends
from typing import List
from ..config_models import AppConfig
from .auth import get_current_user, get_app_config

router = APIRouter(tags=["Configuration"])

@router.get("/config", response_model=dict)
async def get_config_endpoint(current_user: dict = Depends(get_current_user), config: AppConfig = Depends(get_app_config)):
    """Get current application configuration"""
    return config.model_dump()

@router.put("/config/whitelisted-libs")
async def update_whitelisted_libs(
    libs: List[str],
    current_user: dict = Depends(get_current_user)
):
    """Update whitelisted libraries"""
    success = AppConfig.update_user_config_section("WHITELISTED_LIBS", libs)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update whitelisted libraries")

    return {"message": "Whitelisted libraries updated successfully", "libraries": libs}

@router.put("/config/blacklisted-libs")
async def update_blacklisted_libs(
    libs: List[str],
    current_user: dict = Depends(get_current_user)
):
    """Update blacklisted libraries"""
    success = AppConfig.update_user_config_section("BLACKLISTED_LIBS", libs)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update blacklisted libraries")

    return {"message": "Blacklisted libraries updated successfully", "libraries": libs}

@router.put("/config/blacklisted-functions")
async def update_blacklisted_functions(
    functions: List[str],
    current_user: dict = Depends(get_current_user)
):
    """Update blacklisted functions"""
    success = AppConfig.update_user_config_section("BLACKLISTED_FUNCTIONS", functions)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update blacklisted functions")

    return {"message": "Blacklisted functions updated successfully", "functions": functions}

@router.put("/config/allow-file-operations")
async def update_allow_file_operations(
    allow: bool,
    current_user: dict = Depends(get_current_user)
):
    """Update allow file operations setting"""
    success = AppConfig.update_user_config_section("ALLOW_FILE_OPERATIONS", allow)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update file operations setting")

    return {"message": "File operations setting updated successfully", "allow_file_operations": allow}

@router.put("/config/allow-network-operations")
async def update_allow_network_operations(
    allow: bool,
    current_user: dict = Depends(get_current_user)
):
    """Update allow network operations setting"""
    success = AppConfig.update_user_config_section("ALLOW_NETWORK_OPERATIONS", allow)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update network operations setting")

    return {"message": "Network operations setting updated successfully", "allow_network_operations": allow}

@router.put("/config/allow-system-operations")
async def update_allow_system_operations(
    allow: bool,
    current_user: dict = Depends(get_current_user)
):
    """Update allow system operations setting"""
    success = AppConfig.update_user_config_section("ALLOW_SYSTEM_OPERATIONS", allow)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update system operations setting")

    return {"message": "System operations setting updated successfully", "allow_system_operations": allow}