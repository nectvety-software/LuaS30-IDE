# Development Guide

## Source of truth

- Version: `VERSION`
- Native SDK public API: `sdk/luas30/include/ls30/`
- Firmware boundary: `sdk/luas30/src/abi_resolver.c`
- Runtime: `engine/src/`
- Lua API bridge: `engine/src/runtime_bridge.c`
- Builder: `tools/build.py`
- Device profiles: `profiles/`
- Studio: `studio/`
- Project template: `templates/basic/`

## Development rules

### Native SDK

Không thêm vendor MRE header/static library dependency.

Không gọi firmware symbol trực tiếp từ runtime.

Nếu thêm native feature:

1. public `ls30_*` API;
2. resolver binding;
3. capability nếu optional;
4. Lua bridge nếu cần;
5. documentation;
6. validation.

### Lua

Target Lua 5.1.

Game code không phụ thuộc phím vật lý cụ thể nếu có thể dùng abstraction.

### Python Studio

Giữ UI responsive. Search/build dài nên dùng process/thread thay vì block main Qt thread.

### User data

Không ghi config/cache/venv vào engine installation:

```text
%APPDATA%\LuaS30IDE
```

Project mới:

```text
Documents\LuaS30IDE
```

## Validation

Trước khi đóng gói:

```bat
python tools\validate_tree.py
python tools\validate_native_sdk.py
python tools\validate_complete.py
```

Ngoài ra:

- Python compileall;
- C syntax/build bằng ARM GCC;
- ELF report;
- ZIP integrity.

## Versioning

- major: architecture incompatible;
- minor: engine/SDK feature;
- patch: docs, fixes, compatibility or tooling refinements.

Mọi release nên cập nhật:

```text
VERSION
README.md
doc/release/changelog/CHANGELOG_<version>.md
doc/
doc/ai/SKILL.md nếu workflow thay đổi
doc/ai/PROMPT.md nếu project goals/constraints thay đổi
```

## Hardware truthfulness

Không tuyên bố hardware support nếu chưa test hardware.

Phân biệt rõ:

- source validation;
- ARM compile;
- emulator;
- physical device.
