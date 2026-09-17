# MediaTek MRE Project Wizard 1.13.0

## New-project flow

`File -> New Project`, Welcome, Project Hub and Project Storage all route through the same
creation command. Version 1.13.0 replaces the old one-line project-name dialog with a
MediaTek MRE SDK configuration modal.

The project is not created until the user presses `Lưu thiết lập`.

```text
New Project
    |
    v
Cấu hình MediaTek MRE SDK
    |
    +-- APPNAME
    +-- APPVER
    +-- VENDOR
    +-- Resolution
    +-- MediaTek chipset
    +-- Heap RAM
    |
    v
Validate
    |
    v
Generate unique AppID
    |
    +-- project.json
    +-- .luas30/mre_sdk.json
    +-- template source/assets
```

## Dialog layout

The dialog intentionally follows the supplied reference video:

```text
+-------------------------------------------------------+
| [settings] Cấu hình MediaTek MRE SDK              [x] |
|            Thiết lập thông số ... .vxp                |
+-------------------------------------------------------+
| Tên ứng dụng (APPNAME) | Phiên bản (APPVER)           |
| [                    ] | [ 1.0.0                  ]   |
|                                                       |
| Nhà phát triển (VENDOR)                               |
| [ LuaS30                                           ]  |
|                                                       |
| Màn hình (Resolution)  | Chipset MediaTek             |
| [240x320 ...        v] | [MTK6260 (Nokia 220,225) v] |
|                                                       |
| Dung lượng Heap RAM cấp phát                          |
| [1024 KB (1MB - Tiêu chuẩn game MRE)              v] |
|                                                       |
|                              [Hủy bỏ] [Lưu thiết lập] |
+-------------------------------------------------------+
```

It is a custom frameless Qt dialog, not a native operating-system message box.

## Resolution presets

```text
240x320  QVGA / Nokia default
320x240  QVGA landscape
176x220  compact MRE
128x160  legacy MRE
```

The selected dimensions are written to `screen_width`, `screen_height`, `resolution` and
`resolution_label`.

## MediaTek presets

```text
MTK6260  Nokia 220 / Nokia 225
MTK6261  Nokia 3310 3G / Nokia 216
MTK6250  Q-Mobile / K-Touch family
MTK6225  Legacy MRE 2.0
```

The presets influence the default build profile:

```text
MTK6260 -> nokia225-rm1011
others  -> s30plus-native
```

MTK6225 uses the lighter `File ProMng` API tag; the other presets use
`Audio File ProMng` by default.

These labels are compatibility presets, not a claim that every handset using a given
chipset has identical firmware behavior.

## Heap presets

```text
512 KB
768 KB
1024 KB
1536 KB
2048 KB
```

Recommended defaults are selected when the chipset changes:

```text
MTK6260 -> 1024 KB
MTK6261 -> 1024 KB
MTK6250 -> 768 KB
MTK6225 -> 512 KB
```

The user may override the value before creating the project.

## Project identity

APPNAME is also used as the managed project folder name. The existing Windows-safe project
name validation still applies.

AppID is not shown in the modal because LuaS30 generates a fresh unique positive AppID for
every new managed project.

APPVER is stored as project metadata. The current pure-Python VXP packer does not invent an
undocumented VXP version tag; therefore APPVER is preserved in project/build manifests for
future packer support rather than written into an unknown binary tag.

## Files written

`project.json` receives user-facing build metadata, for example:

```json
{
  "name": "MRE Snake Retro",
  "app_version": "1.0.0",
  "vendor": "LuaS30",
  "appid": 123456789,
  "ram_kb": 1024,
  "screen_width": 240,
  "screen_height": 320,
  "resolution": "240x320",
  "mediatek_chipset": "MTK6260",
  "compat_profile": "nokia225-rm1011",
  "mre_api": "Audio File ProMng"
}
```

`.luas30/mre_sdk.json` stores the wizard-oriented structure used by Studio tooling.

## Build behavior

When Studio/CLI compatibility remains `auto`, `tools/build.py` now respects the project's
explicit `compat_profile`. A user-selected CLI profile still overrides the project preset.

This is important for MTK6260/Nokia 225 projects because the wizard can select the
`nokia225-rm1011` native MRE profile without requiring a second manual setting step.
