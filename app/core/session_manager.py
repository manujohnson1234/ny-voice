"""
In-memory session manager for storing and retrieving session data.
"""
import asyncio
from datetime import datetime
from typing import Any, Dict, Optional
from loguru import logger


class SessionManager:
    """
    Thread-safe in-memory session manager.
    Each session can store arbitrary key-value data.
    """
    
    _instance: Optional['SessionManager'] = None
    _lock: asyncio.Lock = asyncio.Lock()
    
    def __new__(cls):
        """Singleton pattern to ensure one instance across the application."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._sessions: Dict[str, Dict[str, Any]] = {}
            cls._instance._session_metadata: Dict[str, Dict[str, Any]] = {}
        return cls._instance
    
    async def create_session(self, session_id: str, initial_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Create a new session with a unique ID.
        
        Args:
            session_id: Unique session identifier
            initial_data: Optional initial data to store in the session
            
        Returns:
            True if session was created, False if it already exists
        """
        async with self._lock:
            if session_id in self._sessions:
                logger.warning(f"Session {session_id} already exists")
                return False
            
            self._sessions[session_id] = initial_data or {}
            self._session_metadata[session_id] = {
                "created_at": datetime.now().isoformat(),
                "last_accessed": datetime.now().isoformat(),
            }
            logger.info(f"Created new session: {session_id}")
            return True
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session data by session ID.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Session data dictionary or None if session doesn't exist
        """
        async with self._lock:
            if session_id not in self._sessions:
                logger.warning(f"Session {session_id} not found")
                return None
            
            # Update last accessed time
            self._session_metadata[session_id]["last_accessed"] = datetime.now().isoformat()
            return self._sessions[session_id].copy()
    
    async def set_value(self, session_id: str, key: str, value: Any) -> bool:
        """
        Set a value in the session.
        
        Args:
            session_id: Unique session identifier
            key: Key to store the value under
            value: Value to store (can be any type)
            
        Returns:
            True if successful, False if session doesn't exist
        """
        async with self._lock:
            if session_id not in self._sessions:
                logger.warning(f"Session {session_id} not found, creating it")
                self._sessions[session_id] = {}
                self._session_metadata[session_id] = {
                    "created_at": datetime.now().isoformat(),
                    "last_accessed": datetime.now().isoformat(),
                }
            
            self._sessions[session_id][key] = value
            self._session_metadata[session_id]["last_accessed"] = datetime.now().isoformat()
            logger.debug(f"Set {key} for session {session_id}")
            return True
    
    async def get_value(self, session_id: str, key: str, default: Any = None) -> Any:
        """
        Get a value from the session.
        
        Args:
            session_id: Unique session identifier
            key: Key to retrieve
            default: Default value if key doesn't exist
            
        Returns:
            Value associated with the key, or default if not found
        """
        async with self._lock:
            if session_id not in self._sessions:
                logger.warning(f"Session {session_id} not found")
                return default
            
            self._session_metadata[session_id]["last_accessed"] = datetime.now().isoformat()
            return self._sessions[session_id].get(key, default)
    
    async def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Update session with multiple key-value pairs.
        
        Args:
            session_id: Unique session identifier
            data: Dictionary of key-value pairs to update
            
        Returns:
            True if successful, False if session doesn't exist
        """
        async with self._lock:
            if session_id not in self._sessions:
                logger.warning(f"Session {session_id} not found, creating it")
                self._sessions[session_id] = {}
                self._session_metadata[session_id] = {
                    "created_at": datetime.now().isoformat(),
                    "last_accessed": datetime.now().isoformat(),
                }
            
            self._sessions[session_id].update(data)
            self._session_metadata[session_id]["last_accessed"] = datetime.now().isoformat()
            logger.debug(f"Updated session {session_id} with {len(data)} keys")
            return True
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and all its data.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            True if session was deleted, False if it didn't exist
        """
        async with self._lock:
            if session_id not in self._sessions:
                logger.warning(f"Session {session_id} not found")
                return False
            
            del self._sessions[session_id]
            del self._session_metadata[session_id]
            logger.info(f"Deleted session: {session_id}")
            return True
    
    async def delete_value(self, session_id: str, key: str) -> bool:
        """
        Delete a specific key from the session.
        
        Args:
            session_id: Unique session identifier
            key: Key to delete
            
        Returns:
            True if key was deleted, False if session or key doesn't exist
        """
        async with self._lock:
            if session_id not in self._sessions:
                logger.warning(f"Session {session_id} not found")
                return False
            
            if key not in self._sessions[session_id]:
                logger.warning(f"Key {key} not found in session {session_id}")
                return False
            
            del self._sessions[session_id][key]
            self._session_metadata[session_id]["last_accessed"] = datetime.now().isoformat()
            logger.debug(f"Deleted key {key} from session {session_id}")
            return True
    
    async def get_session_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata about a session (created_at, last_accessed, etc.).
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Metadata dictionary or None if session doesn't exist
        """
        async with self._lock:
            if session_id not in self._session_metadata:
                return None
            return self._session_metadata[session_id].copy()
    
    async def list_sessions(self) -> list[str]:
        """
        Get a list of all active session IDs.
        
        Returns:
            List of session IDs
        """
        async with self._lock:
            return list(self._sessions.keys())
    
    async def session_exists(self, session_id: str) -> bool:
        """
        Check if a session exists.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            True if session exists, False otherwise
        """
        async with self._lock:
            return session_id in self._sessions


# Convenience function to get the singleton instance
def get_session_manager() -> SessionManager:
    """Get the singleton SessionManager instance."""
    return SessionManager()

