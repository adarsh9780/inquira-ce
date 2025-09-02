from pydantic import BaseModel, Field
from typing import List, Optional
import json
from pathlib import Path

class AppConfig(BaseModel):
    """Configuration model for the FastAPI application"""

    WHITELISTED_LIBS: List[str] = Field(
        default_factory=list,
        description="Libraries that are allowed to be imported"
    )

    BLACKLISTED_LIBS: List[str] = Field(
        default_factory=list,
        description="Libraries that are not allowed to be imported"
    )

    ALLOWED_FUNCTIONS: List[str] = Field(
        default_factory=list,
        description="Functions that are allowed to be used"
    )

    BLACKLISTED_FUNCTIONS: List[str] = Field(
        default_factory=list,
        description="Functions that are not allowed to be used"
    )

    ALLOW_FILE_OPERATIONS: bool = Field(
        default=False,
        description="Whether file operations are allowed"
    )

    ALLOW_NETWORK_OPERATIONS: bool = Field(
        default=False,
        description="Whether network operations are allowed"
    )

    ALLOW_SYSTEM_OPERATIONS: bool = Field(
        default=False,
        description="Whether system operations are allowed"
    )

    @classmethod
    def from_json_file(cls, file_path: str) -> "AppConfig":
        """Load configuration from a JSON file"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        with open(path, 'r') as f:
            data = json.load(f)

        return cls(**data)

    def is_library_allowed(self, library_name: str) -> bool:
        """Check if a library is allowed"""
        # Check if it's in the blacklist
        if library_name in self.BLACKLISTED_LIBS:
            return False

        # If whitelist is empty, allow everything not blacklisted
        if not self.WHITELISTED_LIBS:
            return True

        # Check if it's in the whitelist
        return library_name in self.WHITELISTED_LIBS

    def is_function_allowed(self, function_name: str) -> bool:
        """Check if a function is allowed"""
        # Check if it's in the blacklist
        if function_name in self.BLACKLISTED_FUNCTIONS:
            return False

        # If whitelist is empty, allow everything not blacklisted
        if not self.ALLOWED_FUNCTIONS:
            return True

        # Check if it's in the whitelist
        return function_name in self.ALLOWED_FUNCTIONS