#!/usr/bin/env python3
"""validate_prior_work_suggest.py — AI Agent gợi ý ý tưởng dựa trên dự án cũ.

Người dùng yêu cầu: agent phải **gợi ý được trong cuộc trò chuyện** (làm game theo
phong cách gì) và phải **xem qua các dự án cũ** ở `Documents\\LuaS30 Projects`.

Cái khó không nằm ở chỗ viết prompt. Nằm ở chỗ: agent bị `project_scope_note` KHOÁ
trong project đang mở — mọi đường dẫn `read`/`grep`/`glob` đều tương đối theo gốc
project và không được đi ra ngoài. Nghĩa là nó **không thể** tự đọc
`..\\mini-farm\\README.md`. Nếu để mặc định thì tính năng này im lặng không chạy:
prompt bảo "xem qua các project" nhưng không có đường nào để xem.

Vì thế IDE quét hộ (`prior_work_service.py`) và nhét kết quả vào prompt. Bài kiểm
này soi bốn tầng, và tầng nào cũng phải chứng minh được bằng thứ chạy thật:

  A. Hợp đồng tĩnh — tool `projects` phải nằm trong `TOOL_NAMES` (quên là khối tool
     bị bỏ IM LẶNG, 0 action, không lỗi), `PROJECT_OPS` phải là MỘT nguồn dùng chung
     cho cả prompt lẫn handler, và skill `game-idea-suggest` phải khám phá được.
  B. Dịch vụ thật trên thư mục tạm — quét, rút genre/phong cách/thông số, tách
     kỹ thuật khỏi phong cách, bỏ qua thư mục không phải dự án, loại project đang
     mở, đệm theo vân tay (sửa README là danh mục phải đổi), chịu được thư mục
     không tồn tại, và handler từ chối op/name sai.
  C. Widget THẬT — dựng `AIChatView` rồi đọc system prompt THẬT, để chứng minh
     `<prior_work>` thật sự đi tới model; và bản gọn/bản đầy đủ phải khác nhau.
  D. Vòng lặp thật — gọi THẲNG `AIChatView._run_tool` với một lời gọi `projects`
     để chứng minh kết quả về tới hội thoại, chứ không chỉ "có chữ trong file".

Chạy:

    QT_QPA_PLATFORM=offscreen QT_QPA_FONTDIR="C:/Windows/Fonts" \
        py -3.12 -u tools/validate_prior_work_suggest.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")

ROOT = Path(__file__).resolve().parent.parent
STUDIO = ROOT / "studio"
sys.path.insert(0, str(STUDIO))

# Phải đặt TRƯỚC khi nạp module: `projects_root()` đọc biến môi trường lúc gọi, và
# phần C dựng widget thật sẽ quét đúng thư mục này. Không chuyển hướng thì bài kiểm
# phụ thuộc vào `Documents` thật của người chấm — kết quả đổi theo máy.
_SANDBOX = Path(tempfile.mkdtemp(prefix="luas30_priorwork_"))
os.environ["LUAS30_PROJECTS"] = str(_SANDBOX / "projects")
os.environ.setdefault("LUAS30_APPDATA", str(_SANDBOX / "appdata"))

PROJECTS_ROOT = Path(os.environ["LUAS30_PROJECTS"])
PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)

errors: list[str] = []


def check(label: str, ok: bool) -> None:
    if not ok:
        errors.append(label)


# ------------------------------------------------------- dựng dự án anh em giả
# Mỗi dự án nhắm đúng một đường rút thông tin, để khi nó hỏng thì biết hỏng ở đâu.
def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _seed_projects() -> None:
    # 1. Đầy đủ: project.json có target + README có mục ## Style và ## Gameplay.
    _write(PROJECTS_ROOT / "PopRunner" / "project.json", """{
  "name": "poprunner", "display_name": "Pop Runner", "appid": 111,
  "app_version": "2.1.0", "ram_kb": 1024, "screen_width": 240,
  "screen_height": 320, "fps": 15
}""")
    _write(PROJECTS_ROOT / "PopRunner" / "README.md", """# Pop Runner — puzzle for MRE

## Style
Pop art comic look: magenta and cyan flats, halftone dots, thick ink outlines.

## Gameplay
Slide the bus out of the traffic jam; 3+ combo clears the board.
24 levels, solvable and verified by the smoke test.
""")
    _write(PROJECTS_ROOT / "PopRunner" / "src" / "game.lua", "-- game\n")
    _write(PROJECTS_ROOT / "PopRunner" / "src" / "gfx.lua", "-- gfx\n")

    # 2. Chỉ có conf.lua khai báo target (project.json KHÔNG có screen/fps/ram)
    #    -> phải rơi xuống conf.lua, nếu không dự án hiện ra trống thông số.
    _write(PROJECTS_ROOT / "PaperFarm" / "project.json",
           '{"name": "PaperFarm", "title": "Paper Farm"}')
    _write(PROJECTS_ROOT / "PaperFarm" / "conf.lua", """return {
    width = 240,
    height = 320,
    fps = 15,
    title = "Paper Farm"
}""")
    _write(PROJECTS_ROOT / "PaperFarm" / "README.md", """# Paper Farm

## Style
Notebook doodle: ballpoint pen outlines over pencil underdrawing on paper.

## Gameplay
Plant a seed, water the crop, harvest it and sell it in the shop.
Seasons change every 28 days.
""")

    # 3. KHÔNG có README: mọi thông tin nằm ở khối comment đầu `main.lua`.
    _write(PROJECTS_ROOT / "NoReadme" / "main.lua", """-- Shift Bound: Kinetic Escape - prototype
-- May chay: Nokia 240x320, 15fps, 1MB RAM.
-- Theme: Notebook Doodle Art (but bi xanh/do + chi)
-- Nhay, dash, wall jump; 5 wave.
local E = engine
""")

    # 4. Không có dấu hiệu nào là dự án -> phải bị BỎ QUA.
    _write(PROJECTS_ROOT / "NotAProject" / "notes.txt", "hello\n")

    # 5. Dự án ĐANG MỞ -> phải bị loại khỏi danh mục.
    _write(PROJECTS_ROOT / "CurrentOne" / "main.lua", "-- current\n")
    _write(PROJECTS_ROOT / "CurrentOne" / "README.md", "# Current One\n\n## Style\npop art\n")


_seed_projects()
CURRENT = PROJECTS_ROOT / "CurrentOne"

# ------------------------------------------------------------------ import
try:
    from app.services.ai_agent_protocol import (
        PROJECT_OPS,
        TOOL_NAMES,
        agent_protocol_prompt,
    )
    from app.services.prior_work_service import (
        MAX_CATALOG_CHARS,
        PriorWorkService,
    )
    from app.services import prior_work_service as pws
except Exception as exc:  # noqa: BLE001 - thiếu môi trường thì báo, đừng im
    print("FAIL")
    print(" -", f"không import được dịch vụ: {exc}")
    raise SystemExit(1)

try:
    from app.views.ai_chat_view import AIChatView
except Exception as exc:  # noqa: BLE001
    errors.append(f"không nạp được AIChatView: {exc}")
    AIChatView = None  # type: ignore[assignment]

# ------------------------------------------------ A. Hợp đồng tĩnh (protocol)
check("tool `projects` KHÔNG có trong TOOL_NAMES (khối tool sẽ bị bỏ im lặng)",
      "projects" in TOOL_NAMES)
check("PROJECT_OPS thiếu op (list/show/styles)",
      set(PROJECT_OPS) == {"list", "show", "styles"})
# MỘT nguồn: service phải import LẠI đúng tuple của protocol, không tự chép.
check("prior_work_service KHÔNG dùng chung PROJECT_OPS với protocol (hai nguồn)",
      getattr(pws, "PROJECT_OPS", None) is PROJECT_OPS)

suggest_prompt = agent_protocol_prompt(
    shell_enabled=True, edit_enabled=True, task_memory=True, prior_work=True
)
for op in PROJECT_OPS:
    check(f"prompt gợi ý KHÔNG nhắc tới op `{op}` của tool projects",
          op in suggest_prompt)
check("prompt thiếu khối SUGGESTIONS (agent không biết phải gợi ý)",
      "SUGGESTIONS (proactive)" in suggest_prompt)
check("prompt thiếu chỉ dẫn về <prior_work>",
      "<prior_work>" in suggest_prompt)
check("prompt thiếu ràng buộc target 240x320",
      "240x320" in suggest_prompt)
# Tắt được: khi không có project thì phần gợi ý phải biến mất hẳn.
check("prior_work=False mà prompt vẫn còn khối SUGGESTIONS",
      "SUGGESTIONS (proactive)" not in agent_protocol_prompt(
          shell_enabled=True, edit_enabled=True, prior_work=False))

# Skill phải khám phá được thật, không chỉ tồn tại trên đĩa.
try:
    from app.services.skill_service import SkillService

    skills = SkillService(ROOT).discover(None)
    names = {skill.name for skill in skills}
    check("skill `game-idea-suggest` không được khám phá (agent không thấy mục lục)",
          "game-idea-suggest" in names)
    entry = next((s for s in skills if s.name == "game-idea-suggest"), None)
    check("skill `game-idea-suggest` thiếu description trong frontmatter",
          bool(entry and entry.description and entry.description != "(no description)"))
except Exception as exc:  # noqa: BLE001
    errors.append(f"không kiểm được skill: {exc}")

# ------------------------------------------------ B. Dịch vụ thật trên đĩa
service = PriorWorkService()
check("projects_root() không trỏ vào thư mục sandbox (bài kiểm sẽ đọc dữ liệu thật)",
      service.root() == PROJECTS_ROOT)

catalog = service.catalog(CURRENT)
folders = {project.folder for project in catalog}
check("bỏ sót dự án có README đầy đủ", "PopRunner" in folders)
check("bỏ sót dự án chỉ khai báo target ở conf.lua", "PaperFarm" in folders)
check("bỏ sót dự án chỉ có main.lua", "NoReadme" in folders)
check("thư mục không phải dự án bị đưa vào danh mục", "NotAProject" not in folders)
check("dự án ĐANG MỞ vẫn nằm trong danh mục (trùng với context sẵn có)",
      "CurrentOne" not in folders)
check("không có dự án nào bị bỏ qua ngoài dự kiến", len(catalog) == 3)

by_folder = {project.folder: project for project in catalog}

pop = by_folder.get("PopRunner")
check("PopRunner: không đọc được display_name từ project.json",
      bool(pop and pop.title == "Pop Runner"))
check("PopRunner: không nhận ra genre puzzle",
      bool(pop and pop.genre == "traffic-puzzle"))
check("PopRunner: không nhận ra phong cách pop-art",
      bool(pop and "pop-art" in pop.styles))
check("PopRunner: thiếu thông số target",
      bool(pop and pop.spec() == "240x320 · 15 FPS · 1024 KB"))
check("PopRunner: không đếm được số màn", bool(pop and pop.level_count == "24 màn"))
check("PopRunner: không đếm được mô-đun src/", bool(pop and len(pop.modules) == 2))
check("PopRunner: thiếu bằng chứng trích từ README",
      bool(pop and pop.evidence and "halftone" in pop.evidence[0]))

paper = by_folder.get("PaperFarm")
check("PaperFarm: KHÔNG rơi xuống conf.lua để lấy 240x320 (hiện ra trống thông số)",
      bool(paper and paper.screen == "240x320"))
check("PaperFarm: không lấy được fps từ conf.lua", bool(paper and paper.fps == "15 FPS"))
check("PaperFarm: không nhận ra genre farming", bool(paper and paper.genre == "farming-sim"))
check("PaperFarm: không nhận ra phong cách notebook-doodle",
      bool(paper and "notebook-doodle" in paper.styles))

noreadme = by_folder.get("NoReadme")
check("NoReadme: không lấy được bằng chứng từ header main.lua",
      bool(noreadme and noreadme.evidence and "Kinetic Escape" in noreadme.evidence[0]))
check("NoReadme: không lấy được 240x320 từ comment main.lua",
      bool(noreadme and noreadme.screen == "240x320"))
check("NoReadme: không đổi được '1MB RAM' thành KB",
      bool(noreadme and noreadme.ram_kb == "1024 KB"))
check("NoReadme: không nhận ra phong cách notebook-doodle",
      bool(noreadme and "notebook-doodle" in noreadme.styles))
check("NoReadme: genre 'khác' dù có đủ từ khoá platformer",
      bool(noreadme and noreadme.genre == "platformer"))

# Kỹ thuật phải TÁCH khỏi phong cách: nếu trộn vào thì bảng xếp hạng phong cách bị
# "procedural" chiếm đầu và che mất tín hiệu thật.
styles = dict(service.style_profile(CURRENT))
check("'procedural' bị trộn vào bảng phong cách (che mất tín hiệu thật)",
      "procedural-flat" not in styles and "procedural" not in styles)
check("phong cách lặp lại không đếm được notebook-doodle",
      styles.get("notebook-doodle", 0) >= 2)

# Đệm theo VÂN TAY NỘI DUNG: sửa README là danh mục phải đổi. Nếu không, danh mục
# phục vụ bản cũ và người dùng thấy agent nói về dự án như cách đây mấy phiên.
#
# Phải dùng LẠI ĐÚNG instance này, không tạo instance mới: đệm là thuộc tính của
# từng instance, nên một `PriorWorkService()` mới toanh có đệm rỗng và luôn đọc lại
# từ đĩa — nó sẽ xanh kể cả khi vân tay bị phá hoàn toàn. Ứng dụng thật giữ MỘT
# service và gọi `catalog()` mỗi lượt, nên đây mới là kịch bản cần canh.
first_block = service.prompt_block(CURRENT)
first_styles = dict(service.style_profile(CURRENT))
check("nền: PopRunner phải là pop-art trước khi sửa README",
      "pop-art" in by_folder["PopRunner"].styles)
_write(PROJECTS_ROOT / "PopRunner" / "README.md",
       "# Pop Runner\n\n## Style\nComic noir look: silhouette and gothic parchment.\n")
after = {p.folder: p for p in service.catalog(CURRENT)}
check("đệm không tự vô hiệu khi README đổi (danh mục phục vụ bản cũ)",
      "comic-noir" in after["PopRunner"].styles)
check("danh mục đổi nhưng prompt_block thì không",
      service.prompt_block(CURRENT) != first_block)
check("style_profile() vẫn trả kết quả cũ sau khi README đổi",
      dict(service.style_profile(CURRENT)) != first_styles)

# Thư mục không tồn tại: phải trả rỗng, KHÔNG được ném lỗi.
missing = PriorWorkService(root=_SANDBOX / "khong_ton_tai")
check("thư mục dự án không tồn tại mà catalog() ném lỗi",
      missing.catalog(None) == [])
check("thư mục dự án không tồn tại mà prompt_block() vẫn trả nội dung",
      missing.prompt_block(None) == "")
check("thư mục dự án không tồn tại mà execute(list) ném lỗi",
      "chưa có dự án" in missing.execute(None, {"op": "list"}))

# Bản gọn phải NGẮN HƠN HẲN bản đầy đủ, nhưng vẫn chỉ được đường tới tool.
full_block = service.prompt_block(CURRENT, full=True)
brief_block = service.prompt_block(CURRENT, full=False)
check("bản gọn không ngắn hơn bản đầy đủ (tiết kiệm ngữ cảnh vô nghĩa)",
      len(brief_block) < len(full_block))
check("bản gọn thiếu câu chỉ đường tới tool `projects`",
      '"tool":"projects"' in brief_block and '"op":"list"' in brief_block)
check("bản gọn vẫn nhét từng dòng dự án (không tiết kiệm được gì)",
      "PopRunner ·" not in brief_block)
check("bản đầy đủ thiếu dòng dự án", "- PopRunner ·" in full_block)
check("khối prompt vượt trần MAX_CATALOG_CHARS", len(full_block) <= MAX_CATALOG_CHARS + 400)

# Handler phải TỪ CHỐI op sai và name sai, không được trả rỗng im lặng.
# `op` thiếu/rỗng thì CỐ Ý mặc định về "list" (giống tool `skill`): đó là op chỉ-đọc
# an toàn, và model quên `op` là lỗi phổ biến nhất — biến nó thành thông báo lỗi chỉ
# tốn thêm một lượt. Nhưng op LẠ thì phải ném lỗi, vì âm thầm coi là "list" sẽ giấu
# mất lệch pha giữa prompt và handler (model gọi đúng prompt, handler làm việc khác).
check("op thiếu mà không mặc định về list (model quên args.op là mất một lượt)",
      "PopRunner" in service.execute(CURRENT, {}))
check("op rỗng mà không mặc định về list",
      "PopRunner" in service.execute(CURRENT, {"op": ""}))
for bad in ("khong_co_op_nay", "delete", "reset"):
    try:
        service.execute(CURRENT, {"op": bad})
        errors.append(f"handler nhận op không hợp lệ {bad!r} mà không báo lỗi")
    except ValueError as exc:
        # Phải từ chối vì OP SAI, không phải vì rơi xuống nhánh show rồi thiếu
        # args.name. Hai đường đó cùng ném ValueError, nên nếu chỉ bắt loại lỗi thì
        # guard vẫn xanh khi việc kiểm tra op bị xoá — xanh vì lý do sai.
        message = str(exc)
        if bad not in message or "args.name" in message:
            errors.append(
                f"op {bad!r} bị từ chối vì lý do sai (không phải vì op không hợp lệ): {message}"
            )
try:
    service.execute(CURRENT, {"op": "show", "name": "khong_ton_tai"})
    errors.append("handler nhận name không tồn tại")
except ValueError:
    pass
try:
    service.execute(CURRENT, {"op": "show"})
    errors.append("handler op=show thiếu args.name mà không báo lỗi")
except ValueError:
    pass

detail = service.execute(CURRENT, {"op": "show", "name": "PaperFarm"})
check("op=show không trả chi tiết dự án", "PaperFarm" in detail and "notebook-doodle" in detail)
check("op=show không nói rõ agent KHÔNG đọc trực tiếp được",
      "KHÔNG mở trực tiếp" in detail)
listing = service.execute(CURRENT, {"op": "list"})
check("op=list không liệt kê dự án", "PaperFarm" in listing and "PopRunner" in listing)
check("op=styles không trả gu tổng hợp", "GU LÀM GAME" in service.execute(CURRENT, {"op": "styles"}))

# ------------------------------- C. Widget THẬT: prompt do AIChatView lắp ráp
# Phần B kiểm dịch vụ. Phần C dựng `AIChatView` THẬT rồi đọc system prompt THẬT —
# chứng minh khối danh mục thật sự đi tới model, chứ không chỉ là hàm không ai gọi.
try:
    from PySide6.QtWidgets import QApplication

    from app.views.ai_chat_view import AIChatView as _RealView

    QApplication.instance() or QApplication([])
    view = _RealView(ROOT)
    view.set_project_root(CURRENT)
    context = "<codebase_context>…</codebase_context>"

    # (1) Lượt BÀN VỀ Ý TƯỞNG -> phải có danh mục ĐẦY ĐỦ.
    idea_prompt = view._system_prompt(context, "làm game gì bây giờ, gợi ý đi")
    check("prompt lượt hỏi ý tưởng thiếu <prior_work>", "<prior_work>" in idea_prompt)
    check("prompt lượt hỏi ý tưởng thiếu dòng dự án cụ thể",
          "PaperFarm" in idea_prompt and "PopRunner" in idea_prompt)
    check("prompt lượt hỏi ý tưởng thiếu khối SUGGESTIONS",
          "SUGGESTIONS (proactive)" in idea_prompt)
    check("prompt lượt hỏi ý tưởng thiếu tên skill để nạp",
          "game-idea-suggest" in idea_prompt)

    # (2) Lượt SỬA LỖI bình thường -> chỉ bản gọn, không mang cả danh mục.
    fix_prompt = view._system_prompt(context, "sửa lỗi dòng 40 trong main.lua")
    check("prompt lượt sửa lỗi vẫn mang cả danh mục dự án (tốn token vô ích)",
          "- PopRunner ·" not in fix_prompt)
    check("prompt lượt sửa lỗi mất hẳn <prior_work> (agent không biết có danh mục)",
          "<prior_work>" in fix_prompt)

    # (3) Nhận biết lượt hỏi ý tưởng — sai một chiều vẫn an toàn nhưng phải đúng
    #     ở các câu rõ ràng.
    for question in ("gợi ý ý tưởng", "làm game theo phong cách gì",
                     "nên làm cái gì bây giờ", "give me ideas", "what should i build"):
        check(f"không nhận ra lượt hỏi ý tưởng: {question!r}",
              view._question_wants_ideas(question) is True)
    for question in ("sửa lỗi dòng 40", "thêm nút pause vào menu", "build giúp tôi"):
        check(f"nhận nhầm lượt làm việc thành lượt hỏi ý tưởng: {question!r}",
              view._question_wants_ideas(question) is False)

    # (4) Project trống -> coi như đang dựng cái mới, phải kèm danh mục đầy đủ.
    empty_project = PROJECTS_ROOT / "BrandNew"
    empty_project.mkdir(parents=True, exist_ok=True)
    view.set_project_root(empty_project)
    check("project trống mà không kèm danh mục đầy đủ (đang cân nhắc làm gì)",
          "- PaperFarm ·" in view._system_prompt(context, "chào bạn"))

    # (5) Không có project -> khối phải biến mất hẳn, không để lại rác.
    #     Bất biến quan trọng: có <prior_work> ⟺ có khối SUGGESTIONS. Lệch nhau là
    #     trạng thái nửa vời — hoặc có danh mục mà không biết dùng, hoặc được bảo
    #     "hãy gợi ý" mà không có gì để gợi ý.
    view.set_project_root(None)
    bare = view._system_prompt(context, "gợi ý ý tưởng đi")
    check("không có project mà prompt vẫn có <prior_work>", "<prior_work>" not in bare)
    check("không có project mà prompt vẫn có khối SUGGESTIONS",
          "SUGGESTIONS (proactive)" not in bare)
    for label, prompt in (("có project + hỏi ý tưởng", idea_prompt),
                          ("không có project", bare)):
        check(f"{label}: <prior_work> và SUGGESTIONS lệch nhau",
              ("<prior_work>" in prompt) == ("SUGGESTIONS (proactive)" in prompt))
    check("prompt phình quá lớn", len(idea_prompt) < 60_000)

    # ------------------------------- D. Vòng lặp thật: tool `projects` chạy
    view.set_project_root(CURRENT)
    view._history = []
    view._cancel_requested = False
    from app.services.ai_agent_protocol import ToolAction

    view._run_tool(
        ToolAction(tool="projects", args={"op": "show", "name": "PaperFarm"},
                   reason="Xem chi tiết dự án tương tự"),
        continue_after=False,
    )
    joined = "\n".join(str(item.get("content") or "") for item in view._history)
    check("gọi tool `projects` không để lại kết quả trong hội thoại", "PaperFarm" in joined)
    check("kết quả tool không đi tới model (thiếu tiền tố Tool result)",
          "Tool result for projects" in joined)

    view._history = []
    view._run_tool(
        ToolAction(tool="projects", args={"op": "khong_co"}, reason="op sai"),
        continue_after=False,
    )
    joined = "\n".join(str(item.get("content") or "") for item in view._history)
    check("op sai mà không báo lỗi về hội thoại (im lặng)", "Tool error" in joined)
except Exception as exc:  # noqa: BLE001 - thiếu Qt thì báo, đừng im
    errors.append(f"không dựng được AIChatView thật để kiểm prompt: {exc!r}")

if errors:
    print("FAIL")
    for error in errors:
        print(" -", error)
    raise SystemExit(1)

print("PASS: tool `projects` nằm trong TOOL_NAMES, PROJECT_OPS là một nguồn dùng chung")
print("PASS: prompt có khối SUGGESTIONS + <prior_work>, và tắt được khi không có project")
print("PASS: skill `game-idea-suggest` được khám phá kèm description")
print("PASS: quét đúng dự án (README / conf.lua / main.lua), loại project đang mở và thư mục rác")
print("PASS: đệm tự vô hiệu khi README đổi; thư mục không tồn tại không làm nổ")
print("PASS: bản gọn chỉ ở lượt làm việc, bản đầy đủ ở lượt hỏi ý tưởng và project trống")
print("PASS: tool `projects` chạy thật qua _run_tool và kết quả về tới hội thoại")
