from pydantic import BaseModel, Field
from typing import List, Any
import json
from pathlib import Path

class LoggingConfig(BaseModel):
    """Runtime logging controls."""
    console_level: str = Field(default="ERROR")
    file_level: str = Field(default="DEBUG")
    color_errors: bool = Field(default=True)
    uvicorn_access_log: bool = Field(default=False)

class AppConfig(BaseModel):
    """Configuration model for the FastAPI application"""


    SECURE: bool = Field(
        default=False,
        description="For cookies, use False for development and for production use True")
    LOGGING: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def from_json_file(cls, file_path: str) -> "AppConfig":
        """Load configuration from a JSON file"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        with open(path, 'r') as f:
            data = json.load(f)

        return cls(**data)

    @classmethod
    def get_user_config_path(cls) -> Path:
        """Get the path to the user configuration file"""
        return Path.home() / ".inquira" / "config.json"

    @classmethod
    def load_merged_config(cls, default_config_path: str) -> "AppConfig":
        """Load and merge default config with user config"""
        # Load default config
        default_config = cls.from_json_file(default_config_path)

        # Get user config path
        user_config_path = cls.get_user_config_path()

        # Create user config directory if it doesn't exist
        user_config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load or create user config
        if user_config_path.exists():
            with open(user_config_path, 'r') as f:
                user_data = json.load(f)
        else:
            # Create empty user config
            user_data = {}
            with open(user_config_path, 'w') as f:
                json.dump(user_data, f, indent=2)

        # Merge configs (user config overrides defaults)
        merged_data = default_config.model_dump()
        merged_data.update(user_data)

        return cls(**merged_data)

    def save_user_config(self) -> bool:
        """Save the current config as user config"""
        try:
            user_config_path = self.get_user_config_path()
            user_config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(user_config_path, 'w') as f:
                json.dump(self.model_dump(), f, indent=2)

            return True
        except Exception:
            return False

    @classmethod
    def update_user_config_section(cls, section: str, value: Any) -> bool:
        """Update a specific section of the user config"""
        try:
            user_config_path = cls.get_user_config_path()
            user_config_path.parent.mkdir(parents=True, exist_ok=True)

            # Load existing user config
            if user_config_path.exists():
                with open(user_config_path, 'r') as f:
                    user_data = json.load(f)
            else:
                user_data = {}

            # Update the section
            user_data[section] = value

            # Save updated config
            with open(user_config_path, 'w') as f:
                json.dump(user_data, f, indent=2)

            return True
        except Exception:
            return False
