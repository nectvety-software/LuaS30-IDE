---
name: gameplay
description: Mau co che gameplay cho game LuaS30 (platformer, ban sung, runner, puzzle, battle theo luot, may trang thai, object pool, save diem): code Lua 5.1 dung engine.* chay 240x320 15fps RAM 1MB
---

# Mẫu cơ chế gameplay LuaS30

Dùng skill này khi dựng gameplay mới hoặc sửa logic game đang có. Mọi mẫu
chạy Lua 5.1, `engine.*` only, 240x320, ~15 FPS, heap ~1 MB: **không alloc
trong vòng lặp** (object pool), input qua keypad (`doc/ai/skills/keypad`),
vẽ qua `rect/text/image_region/flush`.

## 0. Khung chung mọi game

```lua
state = "splash"  -- splash | menu | play | pause | over
function engine.load() Game.init() end
function engine.update(dt)
    dt = dt or (1 / 15)
    if state == "play" then Game.update(dt) end
end
function engine.draw()
    engine.clear(BG)
    if state == "splash" then Draw.splash()
    elseif state == "menu" then Draw.menu()
    elseif state == "play" then Game.draw()
    elseif state == "over" then Draw.over() end
    engine.flush()  -- 1 lần/frame, duy nhất
end
```

`splash` tự qua `menu` sau ~2s hoặc phím `ok`. `pause` khi `engine.pause()`,
`resume` vẽ tiếp. Không bao giờ giữ màn hình đen: mọi state đều clear +
vẽ chữ.

## 1. Object pool (bắt buộc cho đạn/hạt/quái)

```lua
Pool = { items = {}, n = 0, max = 24 }
function Pool.init() for i = 1, Pool.max do Pool.items[i] = {on=false} end end
function Pool.spawn(x, y, vx, vy)
    for i = 1, Pool.max do
        local b = Pool.items[i]
        if not b.on then
            b.on, b.x, b.y, b.vx, b.vy = true, x, y, vx, vy
            return b
        end
    end
end
function Pool.update(dt)
    for i = 1, Pool.max do
        local b = Pool.items[i]
        if b.on then
            b.x, b.y = b.x + b.vx * dt, b.y + b.vy * dt
            if b.x < -8 or b.x > 248 then b.on = false end
        end
    end
end
```

Tái dùng bảng, không `table.insert`/`{}` mỗi frame.

## 2. Platformer (nhảy + va chạm tile)

- Trọng lực số nguyên: `vy = vy + 60 * dt`, nhảy `vy = -220` khi `ground`.
- Map tile 16x16 trong mảng 1 chiều `map[row * W + col]`; va chạm chỉ check
  4 góc nhân vật, không quét cả map.
- `ok`/`5` nhảy (kèm buffer 0.1s cho cảm giác tốt), D-Pad/số di chuyển.

## 3. Bắn súng top-down / bullet-hell nhẹ

- Người chơi dưới đáy, bắn lên bằng `ok` (giữ = bắn liên tục theo cooldown
  0.18s, không spawn mỗi frame).
- Địch từ pool bay xuống theo sóng `sin(t)`; va chạm = khoảng cách AABB,
  không pixel-perfect.
- Tối đa ~24 đạn + 10 địch cùng lúc (ngưỡng RAM/CPU 15 FPS).

## 4. Runner vô tận

- Thế giới cuộn sang trái với tốc độ tăng dần; chướng ngại từ pool, khoảng
  cách spawn theo `speed` để luôn qua được ở FPS thấp.
- `ok` nhảy / trượt 2 làn; điểm = `math.floor(dist / 10)`; best lưu file
  (guard `engine.has_files`, save delta như SKILL.md).

## 5. Puzzle lưới (match/cursor)

- Con trỏ ô + `ok` chọn/đổi chỗ, `softright` hủy chọn.
- Rơi + nổ theo cột từ dưới lên; chain tính điểm nhân; không animation dài
  (tối đa 0.25s/hiệu ứng để giữ nhịp 15 FPS).

## 6. Battle theo lượt / menu RPG

- Vòng `menu lệnh → animation ngắn → địch đáp → menu`; HP thanh `rect`,
  text số; `up/down` + wrap + `ok` như Keypad prompt; `softright` chạy trốn.
- Tách data (bảng quái/skill) khỏi code vẽ để cân bằng không cần sửa logic.

## 7. Save điểm/best (optional)

```lua
function Save.best()
    if not engine.has_files then return 0 end
    return tonumber(engine.file_read("best.dat") or 0) or 0
end
function Save.set(v)
    if engine.has_files then engine.file_write("best.dat", tostring(v)) end
end
```

## Definition of done

- Chơi được từ splash → menu → play → over → chơi lại, không kẹt state.
- 60s chơi không giật sâu, không OOM (pool đầy thì bỏ spawn, không alloc).
- `ok`/`softright` hoạt động mọi màn hình; build VXP PASS + smoke emulator.
