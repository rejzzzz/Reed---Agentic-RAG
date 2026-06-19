import sqlite3
import json
import uuid
import datetime
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class ChatMemoryService:
    def __init__(self, db_path: str = "data/chat_history.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        
    def _get_connection(self):
        return sqlite3.connect(self.db_path)
        
    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT,
                    document TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    provider TEXT,
                    created_at TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                )
            ''')
            
            # Migration: add document column if it doesn't exist
            try:
                cursor.execute("ALTER TABLE sessions ADD COLUMN document TEXT")
            except sqlite3.OperationalError:
                pass # Column already exists
                
            conn.commit()
            
    def create_session(self, title: str = "New Conversation", document: Optional[str] = None) -> str:
        session_id = str(uuid.uuid4())
        now = datetime.datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO sessions (session_id, title, document, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, title, document, now, now)
            )
            conn.commit()
        return session_id
        
    def add_message(self, session_id: str, role: str, content: str, provider: Optional[str] = None, document: Optional[str] = None) -> str:
        message_id = str(uuid.uuid4())
        now = datetime.datetime.now().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if session exists, create if not
            cursor.execute("SELECT session_id FROM sessions WHERE session_id = ?", (session_id,))
            if not cursor.fetchone():
                title = content[:30] + "..." if role == "user" else "New Conversation"
                cursor.execute(
                    "INSERT INTO sessions (session_id, title, document, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (session_id, title, document, now, now)
                )
            else:
                # Update session title if it's the first user message and title is default
                if role == "user":
                    cursor.execute("SELECT title, document FROM sessions WHERE session_id = ?", (session_id,))
                    row = cursor.fetchone()
                    if row:
                        if row[0] == "New Conversation":
                            title = content[:30] + "..."
                            cursor.execute("UPDATE sessions SET title = ? WHERE session_id = ?", (title, session_id))
                        
                        # Update document if it wasn't set but is provided now
                        if document and not row[1]:
                            cursor.execute("UPDATE sessions SET document = ? WHERE session_id = ?", (document, session_id))
            
            cursor.execute(
                "INSERT INTO messages (message_id, session_id, role, content, provider, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (message_id, session_id, role, content, provider, now)
            )
            
            cursor.execute(
                "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                (now, session_id)
            )
            conn.commit()
            
        return message_id
        
    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT message_id as id, role, content, provider, created_at as timestamp FROM messages WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT session_id as id, title, document, created_at, updated_at FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_sessions(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT session_id as id, title, document, created_at, updated_at FROM sessions ORDER BY updated_at DESC"
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
    def delete_session(self, session_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            return cursor.rowcount > 0

# Global instance
memory_service = ChatMemoryService()
