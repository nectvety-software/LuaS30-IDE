from pathlib import Path
import json
import tempfile
import sys

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"studio"))

from app.core.app_id import generate_unique_app_id, rewrite_project_identity

with tempfile.TemporaryDirectory() as td:
    root=Path(td)
    seen=set()
    for i in range(50):
        project=root/f"p{i}"
        project.mkdir()
        descriptor=project/"project.json"
        descriptor.write_text(json.dumps({"name":f"p{i}","appid":262567}),encoding="utf-8")
        value=rewrite_project_identity(
            descriptor,
            projects_root=root,
            name=f"p{i}",
            assign_new_app_id=True,
        )
        if value in seen:
            raise SystemExit(f"FAIL: duplicate AppID {value}")
        seen.add(value)
        payload=json.loads(descriptor.read_text(encoding="utf-8"))
        if payload["appid"] != value:
            raise SystemExit("FAIL: project.json AppID was not rewritten")

    candidate=generate_unique_app_id(root)
    if candidate in seen:
        raise SystemExit("FAIL: allocator returned an existing AppID")

print("PASS: generated 50 unique project AppIDs")
print("PASS: generated AppIDs are written to project.json")
print("PASS: allocator excludes existing managed AppIDs")
