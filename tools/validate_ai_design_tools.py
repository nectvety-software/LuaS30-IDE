"""
validate_ai_design_tools.py — AI Agent dùng được công cụ UI Design + Assets.

Kiểm hai tầng:

  A. TĨNH — công cụ có thật sự được nối vào ChatAI và vào prompt của provider,
     và có dùng chung schema với UI Designer hay không (không chép lại).
  B. CHẠY THẬT — dựng một project tạm rồi để "agent" tạo thiết kế và tài nguyên
     qua đúng đường đi thật: khối ```luas30-tool -> parse_agent_response ->
     AIDesignToolService. Gồm cả các trường hợp phải TỪ CHỐI.

Chạy:
    QT_QPA_PLATFORM=offscreen QT_QPA_FONTDIR="C:/Windows/Fonts" \
      py -3.12 -u tools/validate_ai_design_tools.py
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "studio"))

from PySide6.QtGui import QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

FAILS: list[str] = []


def check(label: str, condition: bool, extra: str = "") -> None:
    if not condition:
        FAILS.append(label)
    print(f"  [{'OK  ' if condition else 'FAIL'}] {label} {extra}", flush=True)


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)

    from app.services.ai_agent_protocol import (
        DESIGN_TOOL_NAMES,
        TOOL_NAMES,
        agent_protocol_prompt,
        parse_agent_response,
    )
    from app.services.ai_design_tool_service import (
        ASSET_KINDS,
        ASSET_WRITE_OPS,
        UI_DESIGN_READ_OPS,
        UI_DESIGN_WRITE_OPS,
        AIDesignToolService,
        safe_asset_name,
    )
    from app.views.ui_designer import design_store
    from app.views.ui_designer.items import COMPONENTS, SCREEN_H, SCREEN_W

    service = AIDesignToolService()

    # ------------------------------------------------------------------ A. tĩnh
    print("-- A. nối vào ChatAI + dùng chung schema --", flush=True)
    chat = (ROOT / "studio" / "app" / "views" / "ai_chat_view.py").read_text(encoding="utf-8")
    protocol = (ROOT / "studio" / "app" / "services" / "ai_agent_protocol.py").read_text(encoding="utf-8")
    svc_src = (ROOT / "studio" / "app" / "services" / "ai_design_tool_service.py").read_text(encoding="utf-8")

    check("ChatAI import công cụ thiết kế", "AIDesignToolService" in chat and "ai_design_tool_service" in chat)
    check("ChatAI khởi tạo service", "self.design_tool_service = AIDesignToolService()" in chat)
    check("ChatAI có _run_tool", "def _run_tool(" in chat)
    check("thao tác ghi đi theo access mode", "allow_write=allow_write" in chat and "_edit_policy()" in chat)
    check("prompt quảng bá cả hai công cụ",
          '"tool":"ui_design"' in protocol and '"tool":"asset"' in protocol)
    check("prompt chặn ghi khi không được phép",
          "unavailable in this mode" in protocol and "plan_mode" in protocol)
    check("không chép lại schema thành phần",
          "from app.views.ui_designer.items import" in svc_src and "COMPONENTS" in svc_src)
    check("không tự dựng đường dẫn lưu trữ",
          "design_store" in svc_src and '".luas30"' not in svc_src
          and '"ui_design.json"' not in svc_src and '"ui_design.lua"' not in svc_src)
    check("tên công cụ lấy từ một nguồn duy nhất",
          DESIGN_TOOL_NAMES == ("ui_design", "asset")
          and set(DESIGN_TOOL_NAMES) <= set(TOOL_NAMES)
          and set(("read", "grep", "glob")) <= set(TOOL_NAMES),
          f"{TOOL_NAMES}")
    check("parser nhận khối luas30-tool của công cụ thiết kế",
          len(parse_agent_response(
              "```luas30-tool\n"
              '{"tool":"ui_design","args":{"op":"catalog"},"reason":"x"}\n'
              "```").tool_actions) == 1)
    check("op đọc/ghi tách bạch",
          "catalog" in UI_DESIGN_READ_OPS and "add_item" in UI_DESIGN_WRITE_OPS
          and not set(UI_DESIGN_READ_OPS) & set(UI_DESIGN_WRITE_OPS))
    check("safe_asset_name làm sạch tên tệp",
          safe_asset_name("../../Etc Passwd!.png") == "etc_passwd", safe_asset_name("../../Etc Passwd!.png"))

    # ------------------------------------------------------- B. chạy thật
    print("-- B. agent tạo thiết kế + tài nguyên --", flush=True)
    tmp = Path(tempfile.mkdtemp(prefix="luas30-designtools-"))
    try:
        project = tmp / "project"
        (project / ".luas30").mkdir(parents=True)
        (project / "project.json").write_text('{"name":"agent-design"}', encoding="utf-8")

        def tool(tool_name: str, *, allow_write: bool = False, **args):
            """Gửi đúng khối ```luas30-tool như model, rồi thực thi."""
            payload = json.dumps({"tool": tool_name, "args": args, "reason": "validate"})
            parsed = parse_agent_response(f"```luas30-tool\n{payload}\n```")
            if len(parsed.tool_actions) != 1:
                raise AssertionError(f"wire format failed for {tool_name}: {len(parsed.tool_actions)} actions")
            return service.execute(project, parsed.tool_actions[0], allow_write=allow_write)

        # --- đọc ---
        catalog = tool("ui_design", op="catalog")
        missing = [key for key in COMPONENTS if key not in catalog]
        check("catalog liệt kê mọi thành phần của Designer", not missing, f"missing={missing}")
        check("catalog nêu đúng khung màn hình", f"{SCREEN_W}x{SCREEN_H}" in catalog)
        check("screens trên project trống vẫn có main",
              '"id": "main"' in tool("ui_design", op="screens"))
        check("asset list trên project trống", "ASSETS count=0" in tool("asset", op="list"))

        # --- ghi: từ chối khi chưa được phép ---
        refused = 0
        for name, args in (("ui_design", {"op": "add_item", "type": "button", "x": 0, "y": 0}),
                           ("asset", {"op": "make", "kind": "solid"})):
            try:
                tool(name, **args)
            except ValueError:
                refused += 1
        check("từ chối ghi khi chưa được phép", refused == 2, f"refused={refused}/2")
        check("đọc vẫn chạy khi không được ghi",
              "UI SCREENS" in tool("ui_design", op="screens"))

        # --- ghi: thành phần ---
        out = tool("ui_design", op="add_item", type="button", name="btn start",
                   x=63, y=241, text="Bat dau", allow_write=True)
        check("snap lưới 4px", "x=64 y=240" in out, out)
        check("tên được làm sạch thành ID hợp lệ", "'btn_start'" in out, out)

        auto = tool("ui_design", op="add_item", type="label", x=9999, y=-50, allow_write=True)
        check("tên tự sinh theo quy ước Designer", "'label_1'" in auto, auto)
        check("kẹp vào khung màn hình", f"x={SCREEN_W - 84} y=0" in auto, auto)

        dup = tool("ui_design", op="add_item", type="button", name="btn_start", allow_write=True)
        check("tên trùng được thêm hậu tố", "'btn_start_2'" in dup, dup)

        tool("ui_design", op="add_item", type="image", name="logo", x=8, y=8, w=64, h=64,
             src="assets/ui/logo.png", allow_write=True)
        got = tool("ui_design", op="get", screen="main")
        items = json.loads(got.split("\n", 1)[1])
        check("get trả đúng 4 thành phần", len(items) == 4, f"n={len(items)}")
        check("giữ được trường src", any(i.get("src") == "assets/ui/logo.png" for i in items))

        upd = tool("ui_design", op="update_item", name="btn_start", fields={"x": 70, "y": 250},
                   allow_write=True)
        check("update_item snap lại toạ độ", "x=72 y=248" in upd, upd)
        tool("ui_design", op="update_item", name="btn_start", fields={"text": "Ok"}, allow_write=True)
        items = json.loads(tool("ui_design", op="get", screen="main").split("\n", 1)[1])
        check("update_item đổi được nội dung chữ",
              any(i.get("name") == "btn_start" and i.get("text") == "Ok" for i in items))

        removed = tool("ui_design", op="remove_item", name="logo", allow_write=True)
        check("remove_item", "remaining=3" in removed, removed)

        bad = ""
        try:
            tool("ui_design", op="add_item", type="not_a_widget", allow_write=True)
        except ValueError as exc:
            bad = str(exc)
        check("loại thành phần lạ bị từ chối", "Unknown component type" in bad, bad[:80])

        # --- ghi: màn hình ---
        check("add_screen", "Menu_Chinh" in tool("ui_design", op="add_screen",
                                                id="Menu Chinh", allow_write=True))
        check("rename_screen", "ok" in tool("ui_design", op="rename_screen",
                                            screen="Menu_Chinh", to="options", allow_write=True))
        check("delete_screen", "ok" in tool("ui_design", op="delete_screen",
                                            screen="options", allow_write=True))
        protected = ""
        try:
            tool("ui_design", op="delete_screen", screen="main", allow_write=True)
        except ValueError as exc:
            protected = str(exc)
        check("màn hình main được bảo vệ", "cannot be deleted" in protected, protected[:80])

        # --- tài nguyên: mọi kind ---
        made = {}
        for kind in ASSET_KINDS:
            extra = {"text": "OK"} if kind in {"button", "label"} else {}
            line = tool("asset", op="make", kind=kind, name=f"gen_{kind}", **extra, allow_write=True)
            made[kind] = line
        check("sinh đủ mọi kind tài nguyên", len(made) == len(ASSET_KINDS),
              f"{len(made)}/{len(ASSET_KINDS)}")

        # --- tài nguyên: kiểm tra ảnh THẬT, không chỉ kiểm tên tệp ---
        def load(kind: str) -> QImage:
            rel = made[kind].split()[2]
            return QImage(str(project / rel))

        blank = [k for k in ASSET_KINDS if load(k).isNull()]
        check("mọi tệp là PNG đọc được", not blank, f"null={blank}")

        sizes_ok = all(
            (load(k).width(), load(k).height()) == ASSET_KINDS[k][1:] for k in ASSET_KINDS
        )
        check("kích thước đúng như khai báo", sizes_ok,
              str({k: (load(k).width(), load(k).height()) for k in list(ASSET_KINDS)[:3]}))

        solid = load("solid")
        center = solid.pixelColor(solid.width() // 2, solid.height() // 2)
        check("solid tô đúng màu nội dung mặc định",
              center.name().lower() == "#007acc", center.name())

        frame = load("frame")
        fc = frame.pixelColor(frame.width() // 2, frame.height() // 2)
        check("frame là khung RỖNG (không tô kín)", fc.alpha() == 0, f"alpha={fc.alpha()}")

        button_with = load("button")
        tool("asset", op="make", kind="button", name="gen_plain", allow_write=True)
        plain = QImage(str(project / "assets/ui/gen_plain.png"))
        check("có chữ thì ảnh khác ảnh không chữ", button_with != plain)

        label = load("label")
        opaque = sum(
            1 for y in range(label.height()) for x in range(label.width())
            if label.pixelColor(x, y).alpha() > 0
        )
        check("label có vẽ chữ trên nền trong suốt", opaque > 0, f"pixels={opaque}")

        bg = load("gradient")
        top = bg.pixelColor(bg.width() // 2, 0)
        bottom = bg.pixelColor(bg.width() // 2, bg.height() - 1)
        check("gradient đổi màu theo chiều dọc", top.name() != bottom.name(),
              f"{top.name()} -> {bottom.name()}")

        listed = tool("asset", op="list")
        check("asset list thấy tài nguyên vừa sinh", f"count={len(ASSET_KINDS) + 1}" in listed,
              listed.splitlines()[0])

        bad_target = ""
        try:
            tool("asset", op="make", kind="solid", target="../../evil", allow_write=True)
        except ValueError as exc:
            bad_target = str(exc)
        check("target lạ bị từ chối", "Unknown target" in bad_target, bad_target[:80])
        check("không ghi được ra ngoài project", not (tmp / "evil").exists())

        # --- export ---
        exported = tool("ui_design", op="export", allow_write=True)
        lua_path = project / "ui_design.lua"
        check("export sinh ui_design.lua", lua_path.is_file() and "ok ui_design.lua" in exported, exported)
        lua = lua_path.read_text(encoding="utf-8") if lua_path.is_file() else ""
        check("Lua sinh ra tự chứa (không require tệp khác)",
              "function" in lua and "return" in lua and len(lua) > 2000, f"bytes={len(lua)}")
        check("Lua phản ánh thành phần vừa tạo", "btn_start" in lua)
        check("tài nguyên sinh ra KHÔNG lọt màu chrome IDE", "#f59e0b" not in lua)

        luac = Path("D:/MRE/lua-engine/mre-core/luac/luac.exe")
        if luac.is_file():
            import subprocess
            proc = subprocess.run([str(luac), "-p", str(lua_path)],
                                  capture_output=True, text=True)
            check("luac biên dịch được ui_design.lua", proc.returncode == 0,
                  proc.stderr.strip()[:120])
        else:
            print("  [note] bỏ qua luac -p (không thấy luac.exe)", flush=True)

        # --- đọc lại bằng Designer thật ---
        store = design_store.DesignStore(project)
        check("DesignStore của Designer đọc lại được tệp agent ghi", store.load())
        check("DesignStore thấy đúng số thành phần",
              len(store.screen_items("main")) == 3, f"n={len(store.screen_items('main'))}")
        check("định dạng vẫn là version 2", store.payload.get("version") == design_store.FORMAT_VERSION)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n== KẾT QUẢ ==", flush=True)
    print("FAIL:", FAILS or "không có", flush=True)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
