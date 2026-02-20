from typing import Dict, Any, Optional
import threading
from datetime import datetime, timedelta


class SessionVariableStore:
    """
    In-memory variable store for managing global and local variables per user session.
    Variables persist within a session but are cleared when the app restarts.
    """

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._session_timeout = timedelta(hours=24)  # Match auth session timeout

    def _get_session_key(self, user_id: str) -> str:
        """Generate session key for user"""
        return f"user_{user_id}"

    def _initialize_session(self, user_id: str):
        """Initialize variable storage for a new session"""
        session_key = self._get_session_key(user_id)
        if session_key not in self._store:
            self._store[session_key] = {
                'global_vars': {
                    '__builtins__': __builtins__,
                    '__name__': '__main__',
                    '__doc__': None,
                    '__package__': None,
                },
                'local_vars': {},
                'created_at': datetime.now(),
                'last_accessed': datetime.now()
            }

    def get_global_vars(self, user_id: str) -> Dict[str, Any]:
        """Get global variables for a user session"""
        with self._lock:
            self._initialize_session(user_id)
            session_key = self._get_session_key(user_id)
            session_data = self._store[session_key]
            session_data['last_accessed'] = datetime.now()
            return session_data['global_vars'].copy()

    def get_local_vars(self, user_id: str) -> Dict[str, Any]:
        """Get local variables for a user session"""
        with self._lock:
            self._initialize_session(user_id)
            session_key = self._get_session_key(user_id)
            session_data = self._store[session_key]
            session_data['last_accessed'] = datetime.now()
            return session_data['local_vars'].copy()

    def update_global_vars(self, user_id: str, new_globals: Dict[str, Any]):
        """Update global variables for a user session"""
        with self._lock:
            self._initialize_session(user_id)
            session_key = self._get_session_key(user_id)
            session_data = self._store[session_key]

            # Update global variables, preserving builtins
            for key, value in new_globals.items():
                if key != '__builtins__':
                    session_data['global_vars'][key] = value

            session_data['last_accessed'] = datetime.now()

    def update_local_vars(self, user_id: str, new_locals: Dict[str, Any]):
        """Update local variables for a user session"""
        with self._lock:
            self._initialize_session(user_id)
            session_key = self._get_session_key(user_id)
            session_data = self._store[session_key]

            # Update local variables
            session_data['local_vars'].update(new_locals)
            session_data['last_accessed'] = datetime.now()

    def clear_session(self, user_id: str):
        """Clear all variables for a user session"""
        with self._lock:
            session_key = self._get_session_key(user_id)
            if session_key in self._store:
                del self._store[session_key]

    def cleanup_expired_sessions(self):
        """Clean up expired sessions (called periodically)"""
        with self._lock:
            current_time = datetime.now()
            expired_sessions = []

            for session_key, session_data in self._store.items():
                if current_time - session_data['last_accessed'] > self._session_timeout:
                    expired_sessions.append(session_key)

            for session_key in expired_sessions:
                del self._store[session_key]

            if expired_sessions:
                from ..core.logger import logprint
                logprint(f"Cleaned up {len(expired_sessions)} expired sessions")

    def get_session_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a user's session"""
        with self._lock:
            session_key = self._get_session_key(user_id)
            if session_key in self._store:
                session_data = self._store[session_key]
                return {
                    'user_id': user_id,
                    'created_at': session_data['created_at'].isoformat(),
                    'last_accessed': session_data['last_accessed'].isoformat(),
                    'global_var_count': len(session_data['global_vars']),
                    'local_var_count': len(session_data['local_vars'])
                }
            return None

    def list_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """List all active sessions (for debugging/admin purposes)"""
        with self._lock:
            result = {}
            for session_key, session_data in self._store.items():
                user_id = session_key.replace('user_', '')
                result[user_id] = {
                    'created_at': session_data['created_at'].isoformat(),
                    'last_accessed': session_data['last_accessed'].isoformat(),
                    'global_var_count': len(session_data['global_vars']),
                    'local_var_count': len(session_data['local_vars'])
                }
            return result


# Global instance
session_variable_store = SessionVariableStore()
