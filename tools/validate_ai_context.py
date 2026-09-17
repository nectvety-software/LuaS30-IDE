from pathlib import Path
import tempfile,sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"studio"))
from app.services.codebase_context_service import (
    CodebaseContextService, INSTRUCTION_FILE_LIMIT, INSTRUCTION_TOTAL_BUDGET,
)

errors=[]
with tempfile.TemporaryDirectory() as td:
    root=Path(td);(root/"src").mkdir();(root/"build").mkdir()
    (root/"SKILLS.md").write_text("RULE project",encoding="utf-8")
    (root/"PROMPT.md").write_text("PROMPT small patches",encoding="utf-8")
    (root/"src/main.lua").write_text("function player_move() return 1 end",encoding="utf-8")
    (root/".env").write_text("SECRET=never-send",encoding="utf-8")
    (root/"build/generated.lua").write_text("never context",encoding="utf-8")
    bundle=CodebaseContextService(ROOT).build(root,"player move")
    for token in ("RULE project","PROMPT small patches","main.lua"):
        if token not in bundle.text: errors.append("missing context: "+token)
    for token in ("SECRET=never-send","never context",".env"):
        if token in bundle.text: errors.append("leaked context: "+token)

    # Tài liệu chỉ dẫn phải tới model NGUYÊN VẸN. Từng hỏng thật: PROMPT.md gộp
    # tài liệu Nokia 225 dài 51k ký tự nhưng bị hạn mức 14k cắt mất phần cuối,
    # nên agent không nhận được nội dung mới mà bản ghi vẫn báo "đã nạp".
    prompt = (ROOT/"doc"/"ai"/"PROMPT.md").read_text(encoding="utf-8")
    tail = [ln.strip() for ln in prompt.splitlines() if ln.strip()][-1]
    if tail not in bundle.text:
        errors.append(
            "PROMPT.md bị cắt: dòng cuối không tới được model -> " + tail[:60])
    if "...[truncated" in bundle.text:
        errors.append("tài liệu chỉ dẫn bị cắt; nâng INSTRUCTION_FILE_LIMIT/budget")
    for name in ("SKILLS.md","SKILL.md","PROMPT.md"):
        size = (ROOT/"doc"/"ai"/name).stat().st_size
        if size > INSTRUCTION_FILE_LIMIT:
            errors.append(f"{name} ({size} ký tự) vượt INSTRUCTION_FILE_LIMIT")
    total = sum((ROOT/"doc"/"ai"/n).stat().st_size for n in ("SKILLS.md","SKILL.md","PROMPT.md"))
    if total > INSTRUCTION_TOTAL_BUDGET:
        errors.append(f"bộ tài liệu ({total} ký tự) vượt INSTRUCTION_TOTAL_BUDGET")

# Phép thử ÂM: khi buộc phải cắt, thông báo phải nói rõ đã cắt bao nhiêu — nếu
# không thì lần sau lại là một lần cắt im lặng nữa.
with tempfile.TemporaryDirectory() as td:
    big = Path(td)/"BIG.md"
    big.write_text("x"*1000, encoding="utf-8")
    got = CodebaseContextService._read_text(big, 100)
    if "truncated" not in got or "900" not in got or "1000" not in got:
        errors.append("thông báo cắt không nêu số liệu: " + got[-60:])

if errors:
    print("FAIL")
    for e in errors: print(" -",e)
    raise SystemExit(1)

print("PASS: instruction files loaded")
print("PASS: relevant source/tree context built")
print("PASS: secret/generated content excluded")
print(f"PASS: toàn bộ tài liệu chỉ dẫn tới model nguyên vẹn (hạn mức {INSTRUCTION_FILE_LIMIT}/file, {INSTRUCTION_TOTAL_BUDGET} tổng)")
print("PASS: khi buộc phải cắt, thông báo nêu rõ số ký tự bị bỏ")
