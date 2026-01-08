"""Gestionnaire de base de données pour la persistance des conversations."""

import asyncio
import json
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

import aiosqlite

from ..backends.base import Message, ToolCall
from .logger import get_logger

logger = get_logger("agentichat.utils.database")


class DatabaseManager:
    """Gestionnaire de base de données SQLite pour agentichat."""

    def __init__(self, db_path: Path) -> None:
        """Initialise le gestionnaire de base de données.

        Args:
            db_path: Chemin vers le fichier SQLite
        """
        self.db_path = db_path
        self.session_id: str | None = None

    async def initialize(self) -> None:
        """Initialise la base de données et crée les tables."""
        async with aiosqlite.connect(self.db_path) as db:
            # Table des sessions
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    backend TEXT NOT NULL,
                    model TEXT NOT NULL,
                    metadata TEXT
                )
                """
            )

            # Table des messages
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tool_calls TEXT,
                    created_at REAL NOT NULL,
                    token_count INTEGER,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
                """
            )

            # Table des résumés de compression
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS compressions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    original_count INTEGER NOT NULL,
                    compressed_count INTEGER NOT NULL,
                    summary TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
                """
            )

            # Index
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_compressions_session ON compressions(session_id, created_at)"
            )

            await db.commit()

        logger.info(f"Database initialized at {self.db_path}")

    async def create_session(self, backend: str, model: str) -> str:
        """Crée une nouvelle session.

        Args:
            backend: Nom du backend (ollama, albert)
            model: Nom du modèle

        Returns:
            ID de la session créée
        """
        session_id = str(uuid.uuid4())
        now = time.time()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO sessions (id, created_at, updated_at, backend, model, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, now, now, backend, model, json.dumps({})),
            )
            await db.commit()

        self.session_id = session_id
        logger.info(f"Created new session: {session_id} ({backend}/{model})")
        return session_id

    async def save_message(self, message: Message, token_count: int | None = None) -> None:
        """Sauvegarde un message dans la base de données.

        Args:
            message: Message à sauvegarder
            token_count: Nombre de tokens (optionnel)
        """
        if not self.session_id:
            logger.warning("No active session, cannot save message")
            return

        now = time.time()

        # Sérialiser les tool_calls si présents
        tool_calls_json = None
        if hasattr(message, "tool_calls") and message.tool_calls:
            tool_calls_json = json.dumps([asdict(tc) for tc in message.tool_calls])

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO messages (session_id, role, content, tool_calls, created_at, token_count)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    self.session_id,
                    message.role,
                    message.content or "",
                    tool_calls_json,
                    now,
                    token_count,
                ),
            )

            # Mettre à jour le timestamp de la session
            await db.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (now, self.session_id),
            )

            await db.commit()

    async def get_session_messages(self, session_id: str | None = None) -> list[Message]:
        """Récupère tous les messages d'une session.

        Args:
            session_id: ID de la session (utilise self.session_id si None)

        Returns:
            Liste des messages
        """
        sid = session_id or self.session_id
        if not sid:
            return []

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT role, content, tool_calls
                FROM messages
                WHERE session_id = ?
                ORDER BY created_at ASC
                """,
                (sid,),
            ) as cursor:
                messages = []
                async for row in cursor:
                    # Reconstruire le message
                    msg_dict: dict[str, Any] = {
                        "role": row["role"],
                        "content": row["content"],
                    }

                    # Désérialiser les tool_calls si présents
                    if row["tool_calls"]:
                        tool_calls_data = json.loads(row["tool_calls"])
                        msg_dict["tool_calls"] = [ToolCall(**tc) for tc in tool_calls_data]

                    messages.append(Message(**msg_dict))

                return messages

    async def get_session_stats(self, session_id: str | None = None) -> dict[str, Any]:
        """Récupère les statistiques d'une session.

        Args:
            session_id: ID de la session (utilise self.session_id si None)

        Returns:
            Dictionnaire avec les stats
        """
        sid = session_id or self.session_id
        if not sid:
            return {}

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Infos de session
            async with db.execute(
                "SELECT backend, model, created_at, updated_at FROM sessions WHERE id = ?",
                (sid,),
            ) as cursor:
                session_row = await cursor.fetchone()
                if not session_row:
                    return {}

            # Stats des messages
            async with db.execute(
                """
                SELECT
                    COUNT(*) as message_count,
                    SUM(CASE WHEN role = 'user' THEN 1 ELSE 0 END) as user_messages,
                    SUM(CASE WHEN role = 'assistant' THEN 1 ELSE 0 END) as assistant_messages,
                    SUM(token_count) as total_tokens,
                    SUM(LENGTH(content)) as total_chars
                FROM messages
                WHERE session_id = ?
                """,
                (sid,),
            ) as cursor:
                stats_row = await cursor.fetchone()

            # Stats de compression
            async with db.execute(
                """
                SELECT COUNT(*) as compression_count
                FROM compressions
                WHERE session_id = ?
                """,
                (sid,),
            ) as cursor:
                comp_row = await cursor.fetchone()

            return {
                "session_id": sid,
                "backend": session_row["backend"],
                "model": session_row["model"],
                "created_at": session_row["created_at"],
                "updated_at": session_row["updated_at"],
                "message_count": stats_row["message_count"] or 0,
                "user_messages": stats_row["user_messages"] or 0,
                "assistant_messages": stats_row["assistant_messages"] or 0,
                "total_tokens": stats_row["total_tokens"] or 0,
                "total_chars": stats_row["total_chars"] or 0,
                "compression_count": comp_row["compression_count"] or 0,
            }

    async def save_compression(
        self, original_count: int, compressed_count: int, summary: str
    ) -> None:
        """Sauvegarde une compression de conversation.

        Args:
            original_count: Nombre de messages avant compression
            compressed_count: Nombre de messages après compression
            summary: Résumé généré
        """
        if not self.session_id:
            logger.warning("No active session, cannot save compression")
            return

        now = time.time()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO compressions (session_id, original_count, compressed_count, summary, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (self.session_id, original_count, compressed_count, summary, now),
            )
            await db.commit()

        logger.info(
            f"Saved compression: {original_count} → {compressed_count} messages (session {self.session_id})"
        )

    async def list_sessions(self, limit: int = 10) -> list[dict[str, Any]]:
        """Liste les sessions récentes.

        Args:
            limit: Nombre maximum de sessions à retourner

        Returns:
            Liste des sessions avec leurs métadonnées
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT
                    s.id,
                    s.backend,
                    s.model,
                    s.created_at,
                    s.updated_at,
                    COUNT(m.id) as message_count
                FROM sessions s
                LEFT JOIN messages m ON s.id = m.session_id
                GROUP BY s.id
                ORDER BY s.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ) as cursor:
                sessions = []
                async for row in cursor:
                    sessions.append(dict(row))
                return sessions

    async def delete_session(self, session_id: str) -> None:
        """Supprime une session et tous ses messages.

        Args:
            session_id: ID de la session à supprimer
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            await db.commit()

        logger.info(f"Deleted session: {session_id}")
