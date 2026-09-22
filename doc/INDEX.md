# LuaS30 IDE Documentation

Tất cả tài liệu Markdown của LuaS30 IDE được quản lý tập trung trong thư mục
`doc/`. Ngoại lệ ở thư mục gốc chỉ có `README.md` và `CHANGELOG.md`.

## Cấu trúc

```text
doc/
├── INDEX.md
├── getting-started/
├── architecture/
├── sdk/
├── reference/
├── platform/
├── build/
├── launcher/
├── configuration/
├── studio/
│   └── editor/
├── development/
├── support/
├── ai/
├── legal/
├── toolchain/
└── release/
    ├── changelog/
    └── validation/
```

## Bắt đầu

- [`getting-started/QUICKSTART.md`](getting-started/QUICKSTART.md) — chạy Studio, tạo project và build đầu tiên.
- [`studio/STUDIO_GUIDE.md`](studio/STUDIO_GUIDE.md) — hướng dẫn giao diện Studio.
- [`studio/MODAL_TITLEBAR_1_0_1.md`](studio/MODAL_TITLEBAR_1_0_1.md) — chuẩn hộp thoại modal custom Title Bar + ngoại lệ.
- [`reference/API.md`](reference/API.md) — API Lua `engine.*`.
- [`build/BUILD_VXP.md`](build/BUILD_VXP.md) — pipeline build `.vxp`.

## Kiến trúc / SDK

- [`architecture/ARCHITECTURE.md`](architecture/ARCHITECTURE.md)
- [`sdk/NATIVE_SDK_1_6.md`](sdk/NATIVE_SDK_1_6.md)
- [`sdk/RUNTIME_COMPATIBILITY_1_8_2.md`](sdk/RUNTIME_COMPATIBILITY_1_8_2.md) — capability detection, ABI aliases and firmware fallbacks.
- [`sdk/RUNTIME_COMPAT_MATRIX_1_8_3.md`](sdk/RUNTIME_COMPAT_MATRIX_1_8_3.md) — per-firmware compatibility matrix and symbol-manifest workflow.
- [`platform/DEVICE_COMPATIBILITY.md`](platform/DEVICE_COMPATIBILITY.md)
- [`platform/S30PLUS_HIGH_COMPAT_1_12_0.md`](platform/S30PLUS_HIGH_COMPAT_1_12_0.md) — native MRE SDK build path and Nokia 225 RM-1011 install profile.

## Build / Launcher / Paths

- [`build/BUILD_VXP.md`](build/BUILD_VXP.md)
- [`build/PORTABLE_TOOLCHAIN_1_8_4.md`](build/PORTABLE_TOOLCHAIN_1_8_4.md) — portable ARM GCC PATH/preflight fix.
- [`build/MRE_GCC_BUILD_1_9_7.md`](build/MRE_GCC_BUILD_1_9_7.md) — corrected MRE-style GCC compile/link preflight.
- [`build/TOOLCHAIN_PROFILES_1_10_0.md`](build/TOOLCHAIN_PROFILES_1_10_0.md) — ARM GCC, RVDS/RVCT and ADS1.2 profiles.
- [`build/RELEASE_AND_HARDENING.md`](build/RELEASE_AND_HARDENING.md) — one canonical VXP, **no signing** (IDE produces unsigned VXP), release matrix and hardening.
- [`build/BUILD_RUN_SYNC.md`](build/BUILD_RUN_SYNC.md)
- [`launcher/SMART_LAUNCHER.md`](launcher/SMART_LAUNCHER.md)
- [`configuration/USER_PATHS.md`](configuration/USER_PATHS.md)
- [`toolchain/README.md`](toolchain/README.md)

## Studio

- [`studio/STUDIO_GUIDE.md`](studio/STUDIO_GUIDE.md)
- [`studio/START_PAGE_1_9_2.md`](studio/START_PAGE_1_9_2.md) — default Welcome / Project Storage startup page.
- [`studio/PROJECT_HUB_LAYOUT_1_9_4.md`](studio/PROJECT_HUB_LAYOUT_1_9_4.md) — clean full-width Welcome/Project Storage mode.
- [`studio/LAYOUT_TOGGLES_1_9_5.md`](studio/LAYOUT_TOGGLES_1_9_5.md) — persistent Explorer and Activity Bar buttons/shortcuts.
- [`studio/CLEAN_STARTUP_TABS_1_9_6.md`](studio/CLEAN_STARTUP_TABS_1_9_6.md) — restart without reopening source files.
- [`studio/STARTUP_SCREEN_1_9_8.md`](studio/STARTUP_SCREEN_1_9_8.md) — Welcome, Project Hub or Empty Editor startup selection.
- [`studio/TERMINAL_CONSOLE_1_9_3.md`](studio/TERMINAL_CONSOLE_1_9_3.md) — integrated Console/Terminal bottom panel and shortcuts.
- [`studio/TABBED_WORKSPACE_1_9.md`](studio/TABBED_WORKSPACE_1_9.md)
- [`studio/WORKSPACE_SESSION_1_9_1.md`](studio/WORKSPACE_SESSION_1_9_1.md) — editor groups, tab/project/panel persistence and startup restore. — VS Code-style tool tabs and Project Storage.
- [`studio/VSCODE_UI_1_5.md`](studio/VSCODE_UI_1_5.md)
- [`studio/EXPLORER_TREE_1_6.md`](studio/EXPLORER_TREE_1_6.md)
- [`studio/COMPACT_BOTTOM_PANEL_1_10_1.md`](studio/COMPACT_BOTTOM_PANEL_1_10_1.md) — startup-hidden compact Console/Terminal panel.
- [`studio/DIRECT_TERMINAL_1_10_2.md`](studio/DIRECT_TERMINAL_1_10_2.md) — type commands directly in the integrated terminal surface.
- [`studio/HEX_PANEL_APPID_1_10_3.md`](studio/HEX_PANEL_APPID_1_10_3.md) — colored panel, VXP HEX viewer, unique project AppID.
- [`studio/AI_WORKBENCH_1_11_0.md`](studio/AI_WORKBENCH_1_11_0.md) — AI Workbench: chat sessions, context and review flow.
- [`studio/MEDIATEK_MRE_PROJECT_WIZARD_1_13_0.md`](studio/MEDIATEK_MRE_PROJECT_WIZARD_1_13_0.md) — new-project MediaTek MRE SDK configuration modal.
- [`studio/AI_AGENT_SHELL_1_14_0.md`](studio/AI_AGENT_SHELL_1_14_0.md) — visible AI activity/reasoning summary and approval-based integrated shell control.
- [`studio/AI_WORKBENCH_V1_1_15_0.md`](studio/AI_WORKBENCH_V1_1_15_0.md) — access modes, provider test/apply, shell agent and reviewable AI code changes.
- [`studio/AI_DESIGN_TOOLS.md`](studio/AI_DESIGN_TOOLS.md) — agent `ui_design`/`asset` tools: AI creates UI designs and generates PNG game assets.
- [`studio/AI_GOAL_MODE_1_0_2.md`](studio/AI_GOAL_MODE_1_0_2.md) — Goal Mode (`/goal`): autonomous task loop, checkpoint rollback, context cache, permission modes.
- [`studio/editor/CODE_EDITOR_1_3.md`](studio/editor/CODE_EDITOR_1_3.md)

## Phát triển

- [`development/DEVELOPMENT.md`](development/DEVELOPMENT.md)
- [`support/TROUBLESHOOTING.md`](support/TROUBLESHOOTING.md)
- [`ai/README.md`](ai/README.md) — AI Agent entry point; read this first.
- [`ai/SKILL.md`](ai/SKILL.md) — binding repository workflow and engineering rules.
- [`ai/PROMPT.md`](ai/PROMPT.md) — master implementation contract.

## Pháp lý / Credits

- [`legal/THIRD_PARTY_NOTICES.md`](legal/THIRD_PARTY_NOTICES.md)

## Release history

- [`../CHANGELOG.md`](../CHANGELOG.md) — toàn bộ lịch sử tóm tắt một chỗ.
- [`release/changelog/`](release/changelog/) — changelog đầy đủ theo phiên bản.
- [`release/validation/`](release/validation/) — validation report theo phiên bản.

## Quy tắc quản lý

1. Không đặt tài liệu `.md` mới ở thư mục gốc, ngoại trừ `README.md` và
   `CHANGELOG.md`.
2. Tài liệu phải đặt đúng nhóm chức năng.
3. Khi di chuyển tài liệu, cập nhật link trong `README.md`, `doc/INDEX.md`,
   `wiki/` và tài liệu liên quan.
4. `SKILL.md` và `PROMPT.md` được quản lý tại `doc/ai/`.
5. Changelog và validation không để lẫn với tài liệu sử dụng hàng ngày.
6. Phiên bản mới: thêm mục vào `CHANGELOG.md` gốc (tóm tắt) + tệp chi tiết
   trong `release/changelog/` + report trong `release/validation/`.
