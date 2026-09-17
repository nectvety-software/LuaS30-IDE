from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


CAPABILITY_ORDER = [
    "files", "audio", "images", "touch", "log", "rename", "removable",
    "text_metrics", "line", "clip", "font_select", "ticks", "exit",
    "resource_init", "file_commit",
]


def load_contract(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def resolve_bindings(contract: dict, exports: Iterable[str]) -> tuple[dict, list[dict]]:
    export_set = set(exports)
    resolved: dict[str, str | None] = {}
    selected_aliases: list[dict] = []
    for field, spec in contract["bindings"].items():
        names = list(spec["symbols"])
        selected = next((name for name in names if name in export_set), None)
        resolved[field] = selected
        if selected and selected != names[0]:
            selected_aliases.append({
                "field": field,
                "alias_slot": spec.get("slot"),
                "primary": names[0],
                "selected": selected,
            })
    return resolved, selected_aliases


def _all(resolved: dict, *fields: str) -> bool:
    return all(resolved.get(field) for field in fields)


def _any(resolved: dict, *fields: str) -> bool:
    return any(resolved.get(field) for field in fields)


def native_capabilities(resolved: dict) -> list[str]:
    caps = []
    if _all(resolved, "file_open","file_close","file_read","file_write","file_size"):
        caps.append("files")
    if resolved.get("audio_play"):
        caps.append("audio")
    if _all(resolved, "image_load","image_prop","image_buffer"):
        caps.append("images")
    if resolved.get("reg_pen"):
        caps.append("touch")
    if _any(resolved, "log_info","log_error"):
        caps.append("log")
    if resolved.get("file_rename"):
        caps.append("rename")
    if resolved.get("removable_drive"):
        caps.append("removable")
    if _all(resolved, "string_width","char_height"):
        caps.append("text_metrics")
    if resolved.get("line"):
        caps.append("line")
    if resolved.get("set_clip"):
        caps.append("clip")
    if resolved.get("set_font"):
        caps.append("font_select")
    if resolved.get("ticks"):
        caps.append("ticks")
    if resolved.get("exit_app"):
        caps.append("exit")
    if resolved.get("res_init"):
        caps.append("resource_init")
    if resolved.get("file_commit"):
        caps.append("file_commit")
    return caps


def file_core_native(resolved: dict) -> bool:
    return _all(
        resolved,
        "file_open","file_close","file_read","file_write","file_size","file_delete"
    )


def activated_fallbacks(resolved: dict, native_caps: set[str]) -> list[str]:
    fb = []
    if not resolved.get("res_init"):
        fb.append("resource_init_noop")
    if not resolved.get("screen_w") or not resolved.get("screen_h"):
        fb.append("screen_240x320")
    if not resolved.get("layer_delete"):
        fb.append("layer_delete_noop")
    if not resolved.get("set_clip"):
        fb.append("clip_noop")
    if not resolved.get("set_font"):
        fb.append("font_noop")
    if not resolved.get("string_width"):
        fb.append("text_width_estimate")
    if not resolved.get("char_height"):
        fb.append("font_height_default")
    if not resolved.get("line") and resolved.get("fill_rect"):
        fb.append("line_software")
    if not resolved.get("fill_rect") and resolved.get("line"):
        fb.append("fill_software")
    if not resolved.get("file_commit") and "files" in native_caps:
        fb.append("file_commit_noop")
    if not resolved.get("file_rename") and file_core_native(resolved):
        fb.append("rename_copy_delete")
    if not resolved.get("removable_drive") and resolved.get("system_drive"):
        fb.append("removable_to_system")
    if not resolved.get("audio_stop"):
        fb.append("audio_stop_noop")
    if not resolved.get("audio_playing"):
        fb.append("audio_state_false")
    if not resolved.get("volume"):
        fb.append("audio_volume_noop")
    if not resolved.get("log_info") and not resolved.get("log_error"):
        fb.append("log_noop")
    if not resolved.get("ticks"):
        fb.append("ticks_zero")
    if not resolved.get("exit_app"):
        fb.append("exit_noop")
    if not resolved.get("reg_pen"):
        fb.append("touch_disabled")
    return fb


def missing_required_groups(resolved: dict) -> list[str]:
    missing = []
    if not _all(resolved, "mem_alloc","mem_realloc","mem_free"):
        missing.append("memory")
    if not _all(resolved, "reg_system","reg_key"):
        missing.append("events")
    if not resolved.get("res_load"):
        missing.append("resource")
    if not _all(resolved, "timer_create","timer_delete"):
        missing.append("timer")
    if not _all(resolved, "layer_create","layer_buffer"):
        missing.append("layer")
    if not _any(resolved, "fill_rect","line"):
        missing.append("draw")
    if not resolved.get("textout"):
        missing.append("text")
    if not resolved.get("flush"):
        missing.append("flush")
    return missing


def effective_capabilities(resolved: dict, native_caps: set[str]) -> list[str]:
    caps = set(native_caps)
    if "rename" not in caps and file_core_native(resolved):
        caps.add("rename")
    if "line" not in caps and resolved.get("fill_rect"):
        caps.add("line")
    if "text_metrics" not in caps and resolved.get("textout"):
        caps.add("text_metrics")
    return [name for name in CAPABILITY_ORDER if name in caps]


def evaluate_firmware(contract: dict, manifest: dict) -> dict:
    resolved, aliases = resolve_bindings(contract, manifest.get("exports", []))
    native = native_capabilities(resolved)
    native_set = set(native)
    fallbacks = activated_fallbacks(resolved, native_set)
    missing = missing_required_groups(resolved)
    effective = effective_capabilities(resolved, native_set)

    if missing:
        level = "incompatible"
        final = "FAIL"
    elif aliases or fallbacks:
        level = "degraded"
        final = "DEGRADED"
    else:
        level = "full"
        final = "PASS"

    return {
        "id": manifest.get("id"),
        "label": manifest.get("label", manifest.get("id")),
        "firmware": manifest.get("firmware", "unknown"),
        "evidence": manifest.get("evidence", "unknown"),
        "native_capabilities": native,
        "effective_capabilities": effective,
        "abi_aliases": aliases,
        "fallbacks": fallbacks,
        "missing_required": missing,
        "compatibility_level": level,
        "final_result": final,
        "export_count": len(set(manifest.get("exports", []))),
        "notes": manifest.get("notes", ""),
        "expected": manifest.get("expected", {}),
    }


def verify_expected(row: dict) -> list[str]:
    expected = row.get("expected") or {}
    failures = []
    if "compatibility_level" in expected and row["compatibility_level"] != expected["compatibility_level"]:
        failures.append(
            f'compatibility_level expected {expected["compatibility_level"]}, got {row["compatibility_level"]}'
        )
    if "final_result" in expected and row["final_result"] != expected["final_result"]:
        failures.append(
            f'final_result expected {expected["final_result"]}, got {row["final_result"]}'
        )
    if "alias_count" in expected and len(row["abi_aliases"]) != int(expected["alias_count"]):
        failures.append(f'alias_count expected {expected["alias_count"]}, got {len(row["abi_aliases"])}')
    if "alias_count_min" in expected and len(row["abi_aliases"]) < int(expected["alias_count_min"]):
        failures.append(f'alias_count expected >= {expected["alias_count_min"]}, got {len(row["abi_aliases"])}')
    if "fallback_count" in expected and len(row["fallbacks"]) != int(expected["fallback_count"]):
        failures.append(f'fallback_count expected {expected["fallback_count"]}, got {len(row["fallbacks"])}')
    if "fallback_count_min" in expected and len(row["fallbacks"]) < int(expected["fallback_count_min"]):
        failures.append(f'fallback_count expected >= {expected["fallback_count_min"]}, got {len(row["fallbacks"])}')
    for name in expected.get("fallbacks_include", []):
        if name not in row["fallbacks"]:
            failures.append(f"missing expected fallback: {name}")
    for name in expected.get("missing_required_include", []):
        if name not in row["missing_required"]:
            failures.append(f"missing expected required-group failure: {name}")
    return failures
