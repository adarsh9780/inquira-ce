import asyncio
from typing import Dict, Optional, Any
from datetime import datetime
from fastapi import WebSocket
from ..core.logger import logprint

class ProgressMessenger:
    """Manages progress messages for WebSocket communication"""

    def __init__(self):
        self.processing_messages: list[str] = []
        self.schema_messages: list[str] = []
        self.context_messages: list[str] = []
        self.api_key_messages: list[str] = []
        self.finalization_messages: list[str] = []
        self.current_processing_index = 0
        self.current_schema_index = 0
        self.current_context_index = 0
        self.current_api_key_index = 0
        self.current_finalization_index = 0
        self._load_default_messages()

    def _load_default_messages(self) -> None:
        """Load default progress messages"""
        self.processing_messages = [
            "🔄 Processing your data file...",
            "⚙️ Optimizing database structure...",
            "📊 Analyzing data patterns..."
        ]
        self.schema_messages = [
            "🧠 Analyzing data structure...",
            "🏷️ Identifying column types...",
            "📝 Generating field descriptions..."
        ]
        self.context_messages = [
            "📝 Saving your data context...",
            "🏷️ Categorizing data domain...",
            "💭 Understanding data context..."
        ]
        self.api_key_messages = [
            "🔑 Configuring API key...",
            "🔐 Validating API credentials...",
            "⚙️ Setting up authentication..."
        ]
        self.finalization_messages = [
            "🔒 Securing database connections...",
            "🧹 Cleaning up temporary files...",
            "✅ Validating setup completion..."
        ]


    def get_next_processing_message(self) -> str:
        """Get next processing message"""
        if not self.processing_messages:
            return "🔄 Processing..."
        message = self.processing_messages[self.current_processing_index]
        self.current_processing_index = (self.current_processing_index + 1) % len(self.processing_messages)
        return message

    def get_next_schema_message(self) -> str:
        """Get next schema generation message"""
        if not self.schema_messages:
            return "🧠 Analyzing..."
        message = self.schema_messages[self.current_schema_index]
        self.current_schema_index = (self.current_schema_index + 1) % len(self.schema_messages)
        return message

    def get_next_context_message(self) -> str:
        """Get next context saving message"""
        if not self.context_messages:
            return "📝 Saving context..."
        message = self.context_messages[self.current_context_index]
        self.current_context_index = (self.current_context_index + 1) % len(self.context_messages)
        return message

    def get_next_api_key_message(self) -> str:
        """Get next API key configuration message"""
        if not self.api_key_messages:
            return "🔑 Configuring API..."
        message = self.api_key_messages[self.current_api_key_index]
        self.current_api_key_index = (self.current_api_key_index + 1) % len(self.api_key_messages)
        return message

    def get_next_finalization_message(self) -> str:
        """Get next finalization message"""
        if not self.finalization_messages:
            return "🔒 Finalizing..."
        message = self.finalization_messages[self.current_finalization_index]
        self.current_finalization_index = (self.current_finalization_index + 1) % len(self.finalization_messages)
        return message

    async def send_progress_update(self, websocket: WebSocket, stage: str, progress: Optional[int] = None, message: Optional[str] = None):
        """Send progress update to WebSocket client"""
        update_data: Dict[str, Any] = {
            "type": "progress",
            "stage": stage,
            "timestamp": datetime.now().isoformat()
        }

        if progress is not None:
            update_data["progress"] = progress

        if message:
            update_data["message"] = message
        else:
            # Add appropriate meaningful message based on stage
            if stage == "converting":
                update_data["message"] = "📊 Converting file to database format..."
            elif stage == "generating_schema":
                update_data["message"] = "🧠 Analyzing data structure and generating schema..."
            elif stage == "saving_context":
                update_data["message"] = "📝 Saving data context and configuration..."
            elif stage == "saving_api_key":
                update_data["message"] = "🔑 Configuring API credentials..."
            elif stage == "finalizing":
                update_data["message"] = "🔒 Finalizing setup and validating configuration..."
            elif stage == "starting":
                update_data["message"] = "🚀 Starting data processing pipeline..."
            elif stage == "completed":
                update_data["message"] = "✅ Processing completed successfully!"
            elif stage == "caching_preview":
                update_data["message"] = "⚡ Optimizing data preview performance..."
            else:
                update_data["message"] = f"Processing stage: {stage}..."

        try:
            await websocket.send_json(update_data)
        except Exception as e:
            logprint(f"Error sending WebSocket message: {e}", level="error")


class WebSocketManager:
    """Manages WebSocket connections for real-time communication"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.progress_messenger = ProgressMessenger()

    async def connect(self, user_id: str, websocket: WebSocket):
        """Accept and register a new WebSocket connection"""
        logprint(f"🔌 [WebSocket] Establishing connection for user: {user_id}")
        await websocket.accept()
        self.active_connections[user_id] = websocket

        # Send welcome message
        welcome_message = {
            "type": "connected",
            "message": "Connected to Inquira processing service",
            "timestamp": datetime.now().isoformat()
        }
        logprint(f"📤 [WebSocket] Sending welcome message to user {user_id}: {welcome_message}")
        await websocket.send_json(welcome_message)

        logprint(f"✅ [WebSocket] Connection established for user: {user_id}")

    async def disconnect(self, user_id: str):
        """Remove a WebSocket connection"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logprint(f"🔌 [WebSocket] Connection closed for user: {user_id}")
        else:
            logprint(f"⚠️ [WebSocket] Attempted to disconnect non-existent connection for user: {user_id}")

    async def send_to_user(self, user_id: str, message: dict):
        """Send a message to a specific user"""
        if user_id in self.active_connections:
            try:
                # Log the message being sent
                logprint(f"📤 [WebSocket] Sending to user {user_id}: {message}")

                await self.active_connections[user_id].send_json(message)
                logprint(f"✅ [WebSocket] Message sent successfully to user {user_id}")
            except Exception as e:
                logprint(f"❌ [WebSocket] Error sending message to user {user_id}: {e}", level="error")
                # Remove broken connection
                await self.disconnect(user_id)
        else:
            logprint(f"⚠️ [WebSocket] No active connection for user {user_id}")
            logprint(f"🔍 [WebSocket] Active connections: {list(self.active_connections.keys())}")

    async def broadcast_progress(self, user_id: str, stage: str, progress: Optional[int] = None, message: Optional[str] = None):
        """Send progress update to user"""
        logprint(f"📊 [WebSocket] Broadcasting progress to user {user_id}: stage={stage}, progress={progress}")
        if user_id in self.active_connections:
            logprint(f"📤 [WebSocket] Sending progress update to user {user_id}")
            await self.progress_messenger.send_progress_update(
                self.active_connections[user_id], stage, progress, message
            )
            logprint(f"✅ [WebSocket] Progress update sent successfully to user {user_id}")
        else:
            logprint(f"⚠️ [WebSocket] Cannot broadcast progress - no active connection for user {user_id}")
            logprint(f"🔍 [WebSocket] Active connections: {list(self.active_connections.keys())}")

    def is_connected(self, user_id: str) -> bool:
        """Check if user has an active WebSocket connection"""
        return user_id in self.active_connections

    async def send_error(self, user_id: str, error_message: str):
        """Send error message to user"""
        logprint(f"❌ [WebSocket] Sending error to user {user_id}: {error_message}", level="error")
        await self.send_to_user(user_id, {
            "type": "error",
            "message": error_message,
            "timestamp": datetime.now().isoformat()
        })

    async def send_completion(self, user_id: str, result: dict):
        """Send completion message with results"""
        logprint(f"✅ [WebSocket] Sending completion to user {user_id}")
        logprint(f"🔍 [WebSocket] Completion result keys: {list(result.keys()) if isinstance(result, dict) else 'not dict'}")
        await self.send_to_user(user_id, {
            "type": "completed",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
        logprint(f"✅ [WebSocket] Completion message sent to user {user_id}")


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
