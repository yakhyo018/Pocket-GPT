"""
Conversations in SQLite (the standard library's sqlite3 — no ORM, no server: one local user,
two tables). One connection, guarded by a lock: FastAPI may call it from several threads.
"""

import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    stopped INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS messages_by_conversation ON messages (conversation_id, id);
"""

TITLE_CHARS = 60


@dataclass
class StoredMessage:
    id: int
    role: str
    content: str
    stopped: bool
    created_at: str


@dataclass
class Conversation:
    id: str
    title: str
    created_at: str
    updated_at: str


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec='seconds')


def make_title(first_message: str) -> str:
    """The first user message, on one line, cut at a word near 60 characters."""
    text = ' '.join(first_message.split())
    if len(text) <= TITLE_CHARS:
        return text
    cut = text[:TITLE_CHARS].rsplit(' ', 1)[0]
    return (cut or text[:TITLE_CHARS]) + '…'


class Store:
    def __init__(self, path: str) -> None:
        if path != ':memory:':
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute('PRAGMA foreign_keys = ON')
        self._lock = threading.Lock()
        with self._lock:
            self._db.executescript(SCHEMA)

    def create(self) -> Conversation:
        now = _now()
        conv = Conversation(id=uuid.uuid4().hex, title='', created_at=now, updated_at=now)
        with self._lock, self._db:
            self._db.execute(
                'INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)',
                (conv.id, conv.title, conv.created_at, conv.updated_at),
            )
        return conv

    def recent(self, limit: int = 100) -> list[Conversation]:
        with self._lock:
            rows = self._db.execute(
                'SELECT * FROM conversations ORDER BY updated_at DESC, created_at DESC LIMIT ?',
                (limit,),
            ).fetchall()
        return [Conversation(**dict(row)) for row in rows]

    def get(self, conversation_id: str) -> Conversation | None:
        with self._lock:
            row = self._db.execute(
                'SELECT * FROM conversations WHERE id = ?', (conversation_id,)
            ).fetchone()
        return Conversation(**dict(row)) if row else None

    def messages(self, conversation_id: str) -> list[StoredMessage]:
        with self._lock:
            rows = self._db.execute(
                'SELECT id, role, content, stopped, created_at FROM messages '
                'WHERE conversation_id = ? ORDER BY id',
                (conversation_id,),
            ).fetchall()
        return [StoredMessage(**{**dict(row), 'stopped': bool(row['stopped'])}) for row in rows]

    def add(self, conversation_id: str, role: str, content: str, stopped: bool = False) -> None:
        """Adds a message and touches the conversation; the first user message names it."""
        now = _now()
        with self._lock, self._db:
            self._db.execute(
                'INSERT INTO messages (conversation_id, role, content, stopped, created_at) '
                'VALUES (?, ?, ?, ?, ?)',
                (conversation_id, role, content, int(stopped), now),
            )
            self._db.execute(
                'UPDATE conversations SET updated_at = ?, '
                "title = CASE WHEN title = '' AND ? = 'user' THEN ? ELSE title END WHERE id = ?",
                (now, role, make_title(content), conversation_id),
            )

    def delete(self, conversation_id: str) -> bool:
        with self._lock, self._db:
            cur = self._db.execute('DELETE FROM conversations WHERE id = ?', (conversation_id,))
        return cur.rowcount > 0

    def close(self) -> None:
        self._db.close()
