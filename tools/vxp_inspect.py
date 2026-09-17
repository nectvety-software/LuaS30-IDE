from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

from vxp_pack import MRE_API_BASE, MRE_API_NAMES

TRAILER_SIZE = 86
MARKER = b"\xB4VDE10"

TAG_NAMES = {
    0x01: "vendor",
    0x02: "app_id",
    0x03: "cert_id",
    0x04: "app_name",
    0x0F: "ram_kb",
    0x12: "binding",
    0x13: "permissions",
}


def _text(value: bytes) -> str:
    return value.rstrip(b"\0").decode("utf-8", errors="replace")


def inspect_bytes(data: bytes) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    result: dict = {
        "valid": False,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest().upper(),
        "errors": errors,
        "warnings": warnings,
    }

    if len(data) < TRAILER_SIZE:
        errors.append("File is smaller than the VXP trailer.")
        return result

    trailer_start = len(data) - TRAILER_SIZE
    marker = data[trailer_start:trailer_start + len(MARKER)]
    if marker != MARKER:
        errors.append("VXP trailer marker is invalid.")
        return result

    trailer_cert = struct.unpack_from("<I", data, trailer_start + len(MARKER))[0]
    signature = data[trailer_start + 10:trailer_start + 74]
    tags_pos = struct.unpack_from("<I", data, len(data) - 12)[0]
    result["trailer_cert_id"] = trailer_cert
    result["tags_pos"] = tags_pos
    result["signature_nonzero"] = any(signature)

    if tags_pos <= 0 or tags_pos >= trailer_start:
        errors.append("Tag stream offset is outside the VXP payload.")
        return result

    pos = tags_pos
    tags: dict[int, bytes] = {}
    ordered: list[tuple[int, bytes]] = []
    terminated = False

    while pos + 8 <= trailer_start:
        tag, size = struct.unpack_from("<II", data, pos)
        pos += 8
        if size > trailer_start - pos:
            errors.append(f"Tag 0x{tag:02X} extends past the trailer.")
            break
        value = data[pos:pos + size]
        pos += size
        ordered.append((tag, value))
        if tag != 0:
            tags[tag] = value
        if tag == 0:
            terminated = True
            break

    if not terminated:
        errors.append("Tag stream has no END tag.")
    if pos != trailer_start:
        errors.append("Unexpected gap/data between tag stream and trailer.")

    def u32(tag: int, default=0):
        value = tags.get(tag, b"")
        return struct.unpack("<I", value[:4])[0] if len(value) >= 4 else default

    cert_tag = u32(0x03)
    app_id = u32(0x02)
    ram_kb = u32(0x0F)
    binding = _text(tags.get(0x12, b""))

    # 0x13 = VM_CE_INFO_PERMISSION: lặp [code:LE32][flag:LE32=1], code = 5000+idx.
    # Sai định dạng này khiến firmware báo lỗi quyền và từ chối mở app.
    perm_raw = tags.get(0x13, b"")
    perm_codes: list[int] = []
    perm_names: list[str] = []
    perm_bad: list[int] = []
    for i in range(0, len(perm_raw) - 7, 8):
        code, flag = struct.unpack_from("<II", perm_raw, i)
        perm_codes.append(code)
        if flag != 1:
            perm_bad.append(code)
        index = code - MRE_API_BASE
        if 0 <= index < len(MRE_API_NAMES):
            perm_names.append(MRE_API_NAMES[index])
    invalid_codes = [c for c in perm_codes
                     if not MRE_API_BASE <= c < MRE_API_BASE + len(MRE_API_NAMES)]

    result.update({
        "vendor": _text(tags.get(0x01, b"")),
        "app_id": app_id,
        "cert_id": cert_tag,
        "app_name": _text(tags.get(0x04, b"")),
        "ram_kb": ram_kb,
        "binding_present": bool(binding and binding != "*"),
        "binding_length": len(binding),
        "api_codes": perm_codes,
        "api_names": perm_names,
    })

    # Retail commercial VXPs carry tag 0x03 = 100 with trailer certid = 1 (verified
    # against shipped games). That is the correct stock-signing convention, not a
    # mismatch; writing 100 into the trailer is what retail firmware refuses.
    retail_signed = cert_tag == 100 and trailer_cert == 1
    if cert_tag != trailer_cert and not retail_signed:
        errors.append("Tag cert_id does not match trailer cert_id.")
    if not app_id:
        errors.append("App ID is zero/missing.")
    if ram_kb <= 0:
        errors.append("RAM requirement is zero/missing.")
    if len(perm_raw) % 8:
        errors.append("Tag 0x13 (permissions) is not a whole number of "
                      "[code][flag] pairs.")
    if invalid_codes:
        errors.append(
            "Tag 0x13 contains codes outside the MRE API range "
            f"{MRE_API_BASE}..{MRE_API_BASE + len(MRE_API_NAMES) - 1}: "
            f"{invalid_codes}. The device reports a permission error and "
            "refuses to open the application.")
    if perm_bad:
        errors.append(f"Tag 0x13 entries with flag != 1: {perm_bad}.")

    if retail_signed:
        result["signing_mode"] = "cert100"
        if not any(signature):
            errors.append("Retail cert-id 1 / tag 100 artifact has an empty signature.")
        if binding not in ("", "*"):
            warnings.append("Retail cert100 artifact contains an unexpected device binding.")
    elif trailer_cert == 100:
        result["signing_mode"] = "cert100-nonstandard-trailer"
        if not any(signature):
            errors.append("cert100 trailer has an empty signature.")
        warnings.append(
            "Trailer cert_id 100 is not the retail convention; stock firmware "
            "expects trailer 1 with tag 0x03 = 100 and will refuse this artifact."
        )
        if binding not in ("", "*"):
            warnings.append("cert100 artifact contains an unexpected device binding.")
    elif trailer_cert == 1 and binding and binding != "*":
        result["signing_mode"] = "device-bound"
        if any(signature):
            warnings.append("Device-bound cert-id 1 normally has a zero RSA trailer.")
    elif trailer_cert == 1:
        result["signing_mode"] = "dev"
        if any(signature):
            warnings.append("Dev cert-id 1 contains a non-zero signature.")
    else:
        result["signing_mode"] = f"cert-{trailer_cert}"
        warnings.append("Unknown certificate id; firmware acceptance cannot be inferred.")

    result["valid"] = not errors
    return result


def inspect_file(path: Path) -> dict:
    path = Path(path)
    report = inspect_bytes(path.read_bytes())
    report["path"] = str(path.resolve())
    return report


def write_report(path: Path, report_path: Path) -> dict:
    report = inspect_file(path)
    Path(report_path).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Inspect and validate LuaS30 VXP metadata/trailer.")
    ap.add_argument("vxp", type=Path)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    report = inspect_file(args.vxp)
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(0 if report["valid"] else 2)
