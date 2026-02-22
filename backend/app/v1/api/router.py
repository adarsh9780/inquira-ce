"""Top-level v1 API router."""

from fastapi import APIRouter

from .admin import router as admin_router
from .auth import router as auth_router
from .chat import router as chat_router
from .conversations import router as conversations_router
from .datasets import router as datasets_router
from .runtime import router as runtime_router
from .workspaces import router as workspaces_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(workspaces_router)
router.include_router(datasets_router)
router.include_router(conversations_router)
router.include_router(chat_router)
router.include_router(admin_router)
router.include_router(runtime_router)
