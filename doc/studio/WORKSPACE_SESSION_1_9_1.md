# Workspace Session Restore 1.9.1

LuaS30 Studio 1.9.1 lưu trạng thái workbench theo cơ chế gần VS Code và tự khôi phục ở lần mở tiếp theo.

## File session

Session được lưu bên ngoài thư mục cài engine:

```text
%APPDATA%\LuaS30IDE\config\workspace_session.json
```

Ghi file sử dụng temp-file + replace để giảm nguy cơ session JSON bị ghi dở.

## Trạng thái được lưu

```text
project hiện tại
editor groups
  tab order
  file tabs
  tool tabs
  untitled tabs
  active tab của từng group
active editor group
kích thước các editor group
sidebar
  visible
  Explorer/Search đang active
  splitter sizes
bottom panel
  visible
  OUTPUT/BUILD/PROBLEMS đang active
  panel height
```

Ngoài ra session giữ kích thước cửa sổ trong schema để có thể mở rộng restore window state về sau.

## Editor groups

Workspace giờ sử dụng `EditorGroupManager` thay cho một `QTabWidget` duy nhất.

```text
Editor Workspace
├── Group 0
│   ├── main.lua
│   ├── Assets
│   └── Project Doctor
└── Group 1
    ├── player.lua
    └── Settings
```

View → Split Editor Right tạo group mới. View → Close Editor Group đóng group hiện tại.

Tool tab vẫn giữ nguyên quy tắc duy nhất: cùng một tool không được nhân bản ra nhiều group. Khi tool đã mở ở group khác, lệnh mở tool sẽ focus group/tab đang tồn tại.

File source có thể xuất hiện ở nhiều group nếu session đã lưu như vậy.

## Automatic save

Session được debounce khoảng 450 ms và tự lưu khi:

- mở/đóng/đổi tab;
- đổi active group;
- gõ trong editor;
- save file;
- kéo thay đổi kích thước editor group/sidebar/panel;
- đổi Explorer/Search;
- toggle sidebar/panel;
- đổi project;
- thoát Studio.

Debounce tránh ghi JSON liên tục cho từng phím gõ.

## Restore order

Khi Studio khởi động:

1. đọc `workspace_session.json`;
2. mở project đã lưu nếu thư mục vẫn tồn tại;
3. tạo lại số editor group;
4. mở lại file tabs và tool tabs theo đúng thứ tự group;
5. phục hồi active tab từng group;
6. phục hồi active group;
7. phục hồi group/sidebar/panel splitter sizes;
8. phục hồi panel visibility và OUTPUT/BUILD/PROBLEMS active;
9. nếu session không còn tab hợp lệ, fallback về `main.lua` hoặc Project Storage.

File đã bị xóa/di chuyển được bỏ qua thay vì làm Studio fail startup.

## Session schema

Rút gọn:

```json
{
  "schema": 1,
  "project": "C:/Users/.../Documents/LuaS30IDE/MyGame",
  "editor": {
    "editor_groups": {
      "active_group": 1,
      "group_sizes": [640, 640],
      "groups": [
        {
          "id": "group-0",
          "active_tab": 0,
          "tabs": [
            {"type": "file", "path": ".../main.lua"},
            {"type": "tool", "key": "assets", "title": "Assets"}
          ]
        }
      ]
    },
    "sidebar": {
      "visible": true,
      "active": "explorer",
      "workspace_sizes": [220, 1100]
    },
    "panel": {
      "visible": true,
      "active_index": 1,
      "vertical_sizes": [760, 145]
    }
  }
}
```

## Safety

Workspace session chỉ lưu UI/workbench state. Nó không thay project source hoặc build configuration.

Các file session hỏng, sai schema hoặc project/file không còn tồn tại được bỏ qua an toàn.


## Behavior override in 1.9.6

The original 1.9.1 behavior restored source and untitled tabs. LuaS30 1.9.6 intentionally
changes that behavior: source/untitled tabs are no longer persisted for startup and are
never auto-opened after restart. Project, tool-tab and layout restoration remain active.

See [`CLEAN_STARTUP_TABS_1_9_6.md`](CLEAN_STARTUP_TABS_1_9_6.md).
