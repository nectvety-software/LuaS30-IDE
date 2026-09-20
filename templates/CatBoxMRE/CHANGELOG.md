# CatBoxMRE Changelog

## v0.15.0 — LowMem Boss Skills / Patterns / Comic Cut-ins
- Keeps the low-memory runtime and lowers every heap declaration to 512 KB.
- Fixes the previous metadata mismatch where `conf.lua` still requested 1024 KB.
- Adds boss HUD skill icons and a blinking warning before special attacks.
- Adds four fixed-pool special attack patterns without per-frame table allocation:
  - Moss King: VINE wave.
  - Picnic Brute: RAM shockwave.
  - Phantom Keeper: aimed ORB.
  - Sky Warden: warned vertical BOLT.
- Adds lightweight comic cut-ins using large ROAR!/BOOM!/WHOO!/ZAP! bubbles, shake, panel-break marks and slash accents.
- Reduces FX pool from 16 to 12 and adds only 4 fixed boss-hazard slots to keep object count bounded.
- Production bundler strips indentation, blank lines and full-line comments; `main.lua` is about 88 KB.
- Build memory guard: source <= 92 KB and host compile delta <= 285 KB.

## v0.14.1 — Low-Memory / OOM fix
- Fixed VXPEmu `not enough memory` startup failure by reducing the declared MRE heap from 1024 KB to 768 KB.
- Restored the production runtime to the stable v0.3 core while retaining 26 stages, world map, 4 bosses, NPCs and secret areas.
- Reduced pools: enemies 6, boxes 4, FX 16, audio queue 4.
- Tuned Lua GC and added build-time memory regression guard.
- Production main.lua is ~93 KB instead of ~167 KB in v0.14.0.
- Host Lua compile regression: ~260 KB vs ~430 KB for v0.14.0.

## v0.3.0 — Boss & Secrets
- Redesigned World Map with world cards, progress bars, boss crowns, lock states, secret badges and animated player marker.
- Added 4 bosses: Moss King, Picnic Brute, Phantom Keeper and Sky Warden.
- Added boss arenas, HP bars, distinct attack patterns and goal locking until boss defeat.
- Added NPC dialogue with proximity prompt and multi-line hints.
- Added 4 hidden secret areas entered with DOWN near glowing portals.
- Added persistent secret gems shown on the World Map.
- Added secret-room banners and gem rewards.
- Preserved 26-level progression, 3-star system and Nokia 225 RM-1011 target.

## v0.2.0 — World Journey
- Added 4-world map progression for all 26 stages.
- Added persistent 0–3 star rating per level.
- Added one-way platforms.
- Added floor switches and solid gates.
- Added timed crumble platforms with respawn.
- Added short-hop jump control and improved moving-platform carry.
- Added richer parallax backgrounds, flowers, animated coins/keys, animated enemies and HUD polish.
- Added world-map node UI, star totals, level preview and updated clear screen.
- Preserved Nokia 225 RM-1011 / MTK6260 / 240x320 / 1024 KB target profile.

## v0.1.4
- Added animated procedural player poses: idle, run, jump, fall.
- Added particle FX for jump, coin collect, key collect, spring, stomp, hurt, and checkpoints.
- Added visible checkpoint flags and improved HUD/clear screen.
- Improved moving platform logic so the player is carried by platforms.
- Enhanced enemy procedural graphics and minor motion animation.
- Kept Nokia 225 RM-1011 / MTK6260 profile compatibility.

# Changelog

## 0.1.0
- 12-stage platformer core
- Cat movement, jump buffer, coyote time
- Coins, keys, level goal
- Springs, moving platforms, boxes
- Slug and ghost enemies
- Spikes and crushers
- Save progress, audio ring buffer, debug overlay
- Single-file production bundling and validation

## 0.1.1 - Black screen compatibility fix
- Register callbacks through the LuaS30 `engine.*` lifecycle.
- Render through `engine.clear/rect/text` and flush every frame.
- Convert RGB888 colors to RGB565.
- Normalize lowercase LuaS30 keypad names.
- Add LuaS30 API-shaped renderer smoke test.

## 0.1.2 — LuaS30 IDE/VXPEmu black-screen hotfix
- Fixed a real Lua parse error in the key map: reserved keyword `return` is now `["return"]`.
- Reworked lifecycle binding to follow the working VXP Pixel Editor 0.3.15 project structure.
- Added `src/99_entry.lua` and direct `engine`/`mre` host binding.
- Removed production `_G` / `rawget` dependency.
- Updated `project.json` to LuaS30 Studio-compatible application/profile metadata.
- Added boot diagnostics through `engine.log` and `catbox_boot.log`.
- Added black-screen smoke assertions for clear/rect/text/flush/draw callbacks.
