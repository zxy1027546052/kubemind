import time
from threading import Lock
from typing import Any


class ConversationMemory:
    MAX_TURNS = 10
    TTL_SECONDS = 3600

    def __init__(self) -> None:
        self._store: dict[str, list[dict[str, str]]] = {}
        self._timestamps: dict[str, float] = {}
        self._lock = Lock()

    def get_history(self, session_id: str) -> list[dict[str, str]]:
        with self._lock:
            self._evict_expired()
            messages = self._store.get(session_id, [])
            self._timestamps[session_id] = time.time()
            return list(messages)

    def add_message(self, session_id: str, role: str, content: str) -> None:
        with self._lock:
            if session_id not in self._store:
                self._store[session_id] = []
            self._store[session_id].append({"role": role, "content": content})
            if len(self._store[session_id]) > self.MAX_TURNS:
                self._store[session_id] = self._store[session_id][-self.MAX_TURNS:]
            self._timestamps[session_id] = time.time()

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._store.pop(session_id, None)
            self._timestamps.pop(session_id, None)

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [
            sid for sid, ts in self._timestamps.items()
            if now - ts > self.TTL_SECONDS
        ]
        for sid in expired:
            self._store.pop(sid, None)
            self._timestamps.pop(sid, None)


conversation_memory = ConversationMemory()
