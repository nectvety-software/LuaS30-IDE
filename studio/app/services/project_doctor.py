from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class DoctorIssue:
    severity: str
    message: str


@dataclass(slots=True)
class DoctorReport:
    issues: list[DoctorIssue]

    @property
    def errors(self) -> int:
        return sum(1 for i in self.issues if i.severity == "ERROR")

    @property
    def warnings(self) -> int:
        return sum(1 for i in self.issues if i.severity == "WARN")

    @property
    def ok(self) -> bool:
        return self.errors == 0

    def lines(self) -> list[str]:
        return [f"[{i.severity}] {i.message}" for i in self.issues]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def inspect_project(project: Path, engine_root: Path) -> DoctorReport:
    project = Path(project).resolve()
    engine_root = Path(engine_root).resolve()
    issues: list[DoctorIssue] = []

    if not project.is_dir():
        return DoctorReport([DoctorIssue("ERROR", f"Project folder does not exist: {project}")])

    descriptor = project / "project.json"
    config: dict = {}
    if not descriptor.is_file():
        issues.append(DoctorIssue("ERROR", "project.json is missing."))
    else:
        try:
            config = json.loads(descriptor.read_text(encoding="utf-8-sig"))
            issues.append(DoctorIssue("OK", "project.json parsed successfully."))
        except Exception as exc:
            issues.append(DoctorIssue("ERROR", f"project.json is invalid: {exc}"))

    if not (project / "main.lua").is_file() and not (project / "main.lub").is_file():
        issues.append(DoctorIssue("ERROR", "main.lua/main.lub is missing."))
    else:
        issues.append(DoctorIssue("OK", "Application entry script is present."))

    if config.get("target_profile"):
        issues.append(DoctorIssue(
            "WARN",
            "target_profile is deprecated in LuaS30 1.8.1; builds now produce one generic VXP."
        ))
    issues.append(DoctorIssue("OK", "Runtime target: generic MRE/VXP with capability detection."))

    try:
        ram = int(config.get("ram_kb", 0) or 0)
        if ram and ram > 4096:
            issues.append(DoctorIssue("WARN", f"RAM request is high for constrained VXP targets: {ram} KB."))
    except (TypeError, ValueError):
        issues.append(DoctorIssue("WARN", "ram_kb is not an integer."))

    try:
        fps = int(config.get("fps", 15))
        if fps > 20:
            issues.append(DoctorIssue("WARN", f"{fps} FPS may be expensive on low-end S30+/VXP devices."))
        elif fps < 5:
            issues.append(DoctorIssue("WARN", f"{fps} FPS is unusually low."))
    except (TypeError, ValueError):
        issues.append(DoctorIssue("WARN", "fps is not an integer."))

    total_assets = 0
    asset_count = 0
    assets = project / "assets"
    if assets.is_dir():
        for path in assets.rglob("*"):
            if path.is_file():
                asset_count += 1
                try:
                    total_assets += path.stat().st_size
                except OSError:
                    pass
        issues.append(DoctorIssue("OK", f"Assets: {asset_count} files, {total_assets / 1024:.1f} KB."))
        if total_assets > 3 * 1024 * 1024:
            issues.append(DoctorIssue("WARN", "Asset payload exceeds 3 MB; verify target storage/RAM limits."))

    build = project / "build"
    manifest = build / "sync_manifest.json"
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            vxp = Path(str(data.get("vxp", "")))
            expected = str(data.get("vxp_sha256", "")).upper()
            if vxp.is_file() and expected:
                actual = _sha256(vxp)
                if actual == expected:
                    issues.append(DoctorIssue("OK", "Last VXP matches sync_manifest SHA-256."))
                else:
                    issues.append(DoctorIssue("ERROR", "Last VXP SHA-256 does not match sync_manifest."))
            else:
                issues.append(DoctorIssue("WARN", "Last build manifest does not point to an available VXP."))
        except Exception as exc:
            issues.append(DoctorIssue("WARN", f"Could not inspect last build manifest: {exc}"))
    else:
        issues.append(DoctorIssue("OK", "No previous build manifest; first build has not been produced yet."))

    if not issues:
        issues.append(DoctorIssue("OK", "No issues found."))
    return DoctorReport(issues)
