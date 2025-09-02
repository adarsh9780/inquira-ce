from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import os
import importlib.resources
from .llm_service import LLMService
from . import generate_schema
from .generate_schema import router as schema_router
from .chat import router as chat_router
from .auth import router as auth_router
from .settings import router as settings_router
from .data_preview import router as data_preview_router
from .code_execution import router as code_execution_router
from .api_key import router as api_key_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the lifecycle of the application"""
    print("API server started. Authentication system initialized.")

    # Initialize app state with None values
    app.state.api_key = None
    app.state.data_path = None
    app.state.schema_path = None
    app.state.context = None
    app.state.llm_service = None
    app.state.llm_initialized = False

    yield

    # Cleanup on shutdown
    print("Shutting down API server")

app = FastAPI(
    title="Inquira",
    version="1.0.0",
    lifespan=lifespan
)

def get_ui_dir() -> str:
    """
    Locate the UI directory for StaticFiles.

    Logic
    --------------
    Prefer the packaged UI shipped inside the wheel (``inquira/ui``). If not
    present (e.g., running from the repo before building the wheel), fall back
    to the local dev output at ``frontend/dist``.

    :returns: Absolute path to a directory that FastAPI/Starlette can serve.
    :rtype: str
    """
    # --- variables at the top (per your standard) ---
    packaged_ui = importlib.resources.files("inquira").joinpath("frontend", "dist")  # Traversable, not necessarily a Path
    dev_ui = "/Users/adarshmaurya/Downloads/Projects/vue-ui/dist"

    # Traversable has no `.exists()`. Use `.is_dir()` which implies existence & type.
    # Optionally, tighten by checking for a known file:
    # if packaged_ui.joinpath("index.html").is_file():
    if packaged_ui.is_dir():
        print("Got the UI from wheel")
        return str(packaged_ui)

    print(f"got the UI from Filesystem: {dev_ui}")
    return str(dev_ui)

app.mount("/ui", StaticFiles(directory=get_ui_dir(), html=True), name="ui")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vue dev server
        "http://127.0.0.1:5173",  # Alternative localhost
        "http://localhost:3000",  # Alternative dev port
        "http://127.0.0.1:3000",  # Alternative dev port
        "http://127.0.0.1:8000",
        "http://localhost:8000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["set-cookie"],
)

# Include all routers
app.include_router(auth_router)
app.include_router(api_key_router)
app.include_router(chat_router)
app.include_router(settings_router)
app.include_router(data_preview_router)
app.include_router(schema_router)
app.include_router(code_execution_router)


@app.get("/", tags=["General"])
async def root():
    """
    Root endpoint to check if API is running
    """
    return {"message": "Inquira is running", "version": "1.0.0"}


def run():
    import uvicorn
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=False
    )

if __name__ == "__main__":
    run()
