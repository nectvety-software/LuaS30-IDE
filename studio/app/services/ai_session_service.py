from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path

from app.core.paths import config_dir


@dataclass
class ChatSession:
    id: str
    title: str
    project: str
    created_at: str
    updated_at: str
    provider: str = ""
    model: str = ""
    access_mode: str = "edit_auto"
    messages: list[dict] = field(default_factory=list)


class AIChatSessionStore:
    """Project-scoped persistent chat sessions inspired by OpenCode /sessions."""

    SCHEMA = 1
    MAX_SESSIONS = 120
    MAX_MESSAGES = 240
    MAX_MESSAGE_CHARS = 120_000

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path or (config_dir() / "ai_sessions.json"))

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def project_key(project_root: Path | str | None) -> str:
        if not project_root:
            return "__global__"
        try:
            value = str(Path(project_root).expanduser().resolve())
        except OSError:
            value = str(project_root)
        return os.path.normcase(value)

    def _empty(self) -> dict:
        return {"schema": self.SCHEMA, "active_by_project": {}, "sessions": {}}

    def _load(self) -> dict:
        if not self.path.is_file():
            return self._empty()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return self._empty()
        if not isinstance(payload, dict):
            return self._empty()
        sessions = payload.get("sessions")
        active = payload.get("active_by_project")
        return {
            "schema": self.SCHEMA,
            "active_by_project": active if isinstance(active, dict) else {},
            "sessions": sessions if isinstance(sessions, dict) else {},
        }

    def _save(self, payload: dict) -> None:
        sessions = payload.get("sessions", {})
        if len(sessions) > self.MAX_SESSIONS:
            ordered = sorted(
                sessions.values(),
                key=lambda x: str(x.get("updated_at") or ""),
                reverse=True,
            )[: self.MAX_SESSIONS]
            keep = {str(item.get("id")): item for item in ordered if item.get("id")}
            payload["sessions"] = keep
            payload["active_by_project"] = {
                project: sid
                for project, sid in payload.get("active_by_project", {}).items()
                if sid in keep
            }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        tmp.replace(self.path)

    @classmethod
    def _clean_messages(cls, messages: list[dict] | tuple[dict, ...]) -> list[dict]:
        cleaned: list[dict] = []
        for item in list(messages)[-cls.MAX_MESSAGES :]:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "")
            if role not in {"user", "assistant"}:
                continue
            content = str(item.get("content") or "")[-cls.MAX_MESSAGE_CHARS :]
            row = {"role": role, "content": content}
            if bool(item.get("_internal")):
                row["_internal"] = True
            cleaned.append(row)
        return cleaned

    @staticmethod
    def title_from_messages(messages: list[dict], fallback: str = "New session") -> str:
        for item in messages:
            if item.get("role") == "user" and not item.get("_internal"):
                text = " ".join(str(item.get("content") or "").split())
                if text:
                    return text[:52] + ("…" if len(text) > 52 else "")
        return fallback

    def create(
        self,
        project_root: Path | str | None,
        *,
        provider: str = "",
        model: str = "",
        access_mode: str = "edit_auto",
        title: str = "New session",
    ) -> ChatSession:
        payload = self._load()
        project = self.project_key(project_root)
        now = self._now()
        session = ChatSession(
            id=uuid.uuid4().hex,
            title=title,
            project=project,
            created_at=now,
            updated_at=now,
            provider=str(provider or ""),
            model=str(model or ""),
            access_mode=str(access_mode or "edit_auto"),
            messages=[],
        )
        payload["sessions"][session.id] = asdict(session)
        payload["active_by_project"][project] = session.id
        self._save(payload)
        return session

    def get(self, session_id: str) -> ChatSession | None:
        item = self._load()["sessions"].get(str(session_id or ""))
        if not isinstance(item, dict):
            return None
        try:
            return ChatSession(
                id=str(item.get("id") or session_id),
                title=str(item.get("title") or "New session"),
                project=str(item.get("project") or "__global__"),
                created_at=str(item.get("created_at") or self._now()),
                updated_at=str(item.get("updated_at") or self._now()),
                provider=str(item.get("provider") or ""),
                model=str(item.get("model") or ""),
                access_mode=str(item.get("access_mode") or "edit_auto"),
                messages=self._clean_messages(item.get("messages") or []),
            )
        except (TypeError, ValueError):
            return None

    def active(self, project_root: Path | str | None) -> ChatSession | None:
        payload = self._load()
        project = self.project_key(project_root)
        sid = str(payload["active_by_project"].get(project) or "")
        return self.get(sid) if sid else None

    def set_active(self, project_root: Path | str | None, session_id: str) -> bool:
        payload = self._load()
        project = self.project_key(project_root)
        item = payload["sessions"].get(str(session_id or ""))
        if not isinstance(item, dict) or str(item.get("project")) != project:
            return False
        payload["active_by_project"][project] = str(session_id)
        self._save(payload)
        return True

    def list_sessions(self, project_root: Path | str | None, limit: int = 20) -> list[ChatSession]:
        project = self.project_key(project_root)
        rows: list[ChatSession] = []
        for sid, item in self._load()["sessions"].items():
            if not isinstance(item, dict) or str(item.get("project")) != project:
                continue
            session = self.get(sid)
            if session:
                rows.append(session)
        rows.sort(key=lambda x: x.updated_at, reverse=True)
        return rows[: max(1, int(limit))]

    def update(
        self,
        session_id: str,
        *,
        messages: list[dict] | None = None,
        title: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        access_mode: str | None = None,
    ) -> ChatSession | None:
        payload = self._load()
        item = payload["sessions"].get(str(session_id or ""))
        if not isinstance(item, dict):
            return None
        if messages is not None:
            item["messages"] = self._clean_messages(messages)
            if title is None and str(item.get("title") or "") in {"", "New session"}:
                item["title"] = self.title_from_messages(item["messages"])
        if title is not None:
            item["title"] = str(title).strip()[:80] or "New session"
        if provider is not None:
            item["provider"] = str(provider)
        if model is not None:
            item["model"] = str(model)
        if access_mode is not None:
            item["access_mode"] = str(access_mode)
        item["updated_at"] = self._now()
        payload["sessions"][str(session_id)] = item
        self._save(payload)
        return self.get(str(session_id))

    def rename(self, session_id: str, title: str) -> ChatSession | None:
        return self.update(session_id, title=title)

    def delete(self, session_id: str) -> bool:
        payload = self._load()
        sid = str(session_id or "")
        item = payload["sessions"].pop(sid, None)
        if not isinstance(item, dict):
            return False
        project = str(item.get("project") or "__global__")
        if payload["active_by_project"].get(project) == sid:
            payload["active_by_project"].pop(project, None)
        self._save(payload)
        return True
