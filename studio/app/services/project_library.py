from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.core.app_id import rewrite_project_identity


_INVALID_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = {"CON","PRN","AUX","NUL", *(f"COM{i}" for i in range(1,10)), *(f"LPT{i}" for i in range(1,10))}


def _validate_name(name: str) -> str:
    value = name.strip()
    if not value or value in {".", ".."}:
        raise ValueError("Invalid project name.")
    if _INVALID_NAME.search(value) or value.endswith((" ", ".")) or value.upper() in _RESERVED:
        raise ValueError("Project name contains characters reserved by Windows.")
    return value


IGNORE_SIZE_DIRS = {".git", ".venv", "__pycache__", ".idea", ".pytest_cache"}


@dataclass(slots=True)
class ProjectRecord:
    root: Path
    name: str
    display_name: str
    app_id: str
    runtime_target: str
    modified: float
    size_bytes: int
    file_count: int
    has_build: bool
    vxp_path: Path | None

    @property
    def modified_text(self) -> str:
        try:
            return datetime.fromtimestamp(self.modified).strftime("%Y-%m-%d %H:%M")
        except Exception:
            return "-"

    @property
    def size_text(self) -> str:
        size = float(self.size_bytes)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024.0 or unit == "GB":
                return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
            size /= 1024.0
        return f"{self.size_bytes} B"


class ProjectLibraryService:
    def __init__(self, projects_root: Path, template_root: Path) -> None:
        self.projects_root = Path(projects_root).resolve()
        self.template_root = Path(template_root).resolve()
        self.projects_root.mkdir(parents=True, exist_ok=True)

    def scan(self, max_depth: int = 4) -> list[ProjectRecord]:
        found: list[ProjectRecord] = []
        root_depth = len(self.projects_root.parts)
        for descriptor in self.projects_root.rglob("project.json"):
            try:
                project_root = descriptor.parent.resolve()
                if len(project_root.parts) - root_depth > max_depth:
                    continue
                if any(part in IGNORE_SIZE_DIRS for part in project_root.parts):
                    continue
                found.append(self.inspect(project_root))
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
        # Mot project con nam trong project khac (vi du ban sao trong release/)
        # khong phai project doc lap — chi giu project ngoai cung.
        roots = [record.root for record in found]
        found = [
            record for record in found
            if not any(other != record.root and record.root.is_relative_to(other)
                       for other in roots)
        ]
        found.sort(key=lambda item: item.modified, reverse=True)
        return found

    def inspect(self, root: Path) -> ProjectRecord:
        root = Path(root).resolve()
        descriptor = root / "project.json"
        payload: dict = {}
        if descriptor.is_file():
            try:
                payload = json.loads(descriptor.read_text(encoding="utf-8-sig"))
            except Exception:
                payload = {}

        size_bytes = 0
        file_count = 0
        latest = root.stat().st_mtime
        for path in root.rglob("*"):
            try:
                rel = path.relative_to(root)
            except ValueError:
                continue
            if any(part in IGNORE_SIZE_DIRS for part in rel.parts):
                continue
            if path.is_file():
                try:
                    stat = path.stat()
                except OSError:
                    continue
                file_count += 1
                size_bytes += stat.st_size
                latest = max(latest, stat.st_mtime)

        build = root / "build"
        candidates = sorted(build.glob("*.vxp"), key=lambda p: p.stat().st_mtime, reverse=True) if build.is_dir() else []
        vxp = candidates[0] if candidates else None
        return ProjectRecord(
            root=root,
            name=root.name,
            display_name=str(payload.get("name") or root.name),
            app_id=str(payload.get("appid") or "-"),
            runtime_target=str(payload.get("runtime_target") or "mre-vxp-generic"),
            modified=latest,
            size_bytes=size_bytes,
            file_count=file_count,
            has_build=bool(vxp),
            vxp_path=vxp,
        )

    def import_project(self, source: Path, name: str | None = None) -> Path:
        source = Path(source).resolve()
        if not source.is_dir():
            raise NotADirectoryError(source)
        if not (source / "project.json").is_file():
            raise FileNotFoundError(f"Not a LuaS30 project: {source / 'project.json'}")
        target_name = _validate_name(name or source.name)
        destination = self.projects_root / target_name
        if destination.exists():
            raise FileExistsError(destination)
        shutil.copytree(source, destination, ignore=shutil.ignore_patterns("build", "release", ".git", ".venv", "__pycache__"))
        self._rewrite_identity(destination, target_name, assign_new_app_id=True)
        return destination

    def duplicate(self, source: Path, new_name: str) -> Path:
        source = Path(source).resolve()
        new_name = _validate_name(new_name)
        destination = self.projects_root / new_name
        if destination.exists():
            raise FileExistsError(destination)
        shutil.copytree(source, destination, ignore=shutil.ignore_patterns("build", "release", ".git", ".venv", "__pycache__"))
        self._rewrite_identity(destination, new_name, assign_new_app_id=True)
        return destination

    def rename(self, source: Path, new_name: str) -> Path:
        source = Path(source).resolve()
        new_name = _validate_name(new_name)
        destination = source.with_name(new_name)
        if destination.exists():
            raise FileExistsError(destination)
        source.rename(destination)
        self._rewrite_identity(destination, new_name, assign_new_app_id=False)
        return destination

    def delete(self, source: Path) -> None:
        source = Path(source).resolve()
        if not source.is_dir():
            return
        # Safety: only managed project folders below Documents/LuaS30IDE can be deleted here.
        source.relative_to(self.projects_root)
        if source == self.projects_root:
            raise ValueError("The project storage root cannot be deleted.")
        if not (source / "project.json").is_file():
            raise ValueError("Refusing to delete a folder that is not a LuaS30 project.")
        shutil.rmtree(source)

    def _rewrite_identity(
        self,
        root: Path,
        name: str,
        *,
        assign_new_app_id: bool,
    ) -> int | None:
        descriptor = root / "project.json"
        if not descriptor.is_file():
            return None
        return rewrite_project_identity(
            descriptor,
            projects_root=self.projects_root,
            name=name,
            assign_new_app_id=assign_new_app_id,
        )
