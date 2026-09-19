# Sprite Sheet Cutter — tài liệu extension cho ChatAI

Extension webview của LuaS30 Studio, thư mục `extensions/sprite-sheet/`.
Giao diện: `ui/index.html` (chạy trong QWebEngineView, mở từ menu
**Công cụ → Tiện ích mở rộng → Sprite Sheet Cutter**).

## Chức năng

- Nạp ảnh sprite sheet (file picker / kéo-thả), zoom tới 800%, lưới pixel phủ.
- Ba chế độ cắt: **Thủ công** (kéo khung), **Lưới đều** (cột/hàng/ô/offset/gap,
  có "Tự căn lưới theo vùng đang kéo"), **Bắt biên 1 điểm** (flood-fill theo
  màu nền, có ngưỡng + đệm px).
- Tự động cắt toàn ảnh: quét liên thông vùng khác màu nền (nhận diện màu nền
  cả viền ảnh, không chỉ góc), ngưỡng nền, cỡ tối thiểu/tối đa; có thể chạy
  2 lượt để tách icon nhỏ và panel nền lớn.
- Xoá nền từng mảnh (toggle riêng cho mỗi cut + ngưỡng chung), xuất PNG trong suốt.
- Danh sách mảnh có tên/x/y/w/h chỉnh tay được.

## Cầu nối Studio (`window.luaS30`)

Do host QWebChannel tiêm vào lúc DocumentReady — chỉ tồn tại khi mở trong IDE:

- `window.luaS30.project(cb)` → `{root, name}` hoặc `{root: null}` khi chưa mở dự án.
- `window.luaS30.writeFiles(files, cb)` → ghi các tệp **tương đối trong thư mục
  dự án**; mỗi phần tử là `{path, text}` hoặc `{path, base64}` (base64 chấp nhận
  cả dạng data-URL của `canvas.toDataURL`). Callback nhận
  `{ok, written[], errors[], projectRoot}`. Chặn: đường dẫn tuyệt đối, `..`,
  `.git/.luas30/__pycache__/node_modules`, tệp bí mật của môi trường,
  ≤ 512 tệp/lần, ≤ 8MB/tệp. Ghi thành công sẽ tự làm mới cây tài nguyên.
- `window.luaS30.notify(message, level)` → status bar của Studio.
- Trang phải chạy được cả khi mở bằng trình duyệt thường (fallback .zip qua
  JSZip CDN) — luôn kiểm tra `window.luaS30 && window.luaS30Ready` trước khi gọi.

## Xuất vào dự án

Mặc định ghi vào `assets/sprites/` (ô "Thư mục đích" chỉnh được):

- Mỗi mảnh → `<dir>/<tên>.png` (tên đã safe hoá `[A-Za-z0-9_-]`).
- `<dir>/atlas.json` → `{"source":"sprite-sheet","frames":[{"name","x","y","w","h","transparentBg"}]}` —
  `name` khớp tên tệp PNG (không phần đuôi), `x/y/w/h` là khung gốc trong sheet.

Gợi ý dùng trong `main.lua` (VXPEngine 240×320): tải sheet gốc rồi vẽ từng
frame bằng toạ độ trong atlas.json, hoặc nhập PNG rời vào `res/` theo manifest.
Khi người dùng hỏi "cắt sprite sheet ra sao", nên mở tool này thay vì viết code
cắt ảnh thủ công.
