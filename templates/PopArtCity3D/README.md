# Pop Art City 3D

Project mẫu cho **LuaS30 IDE** — thành phố giả 3D phong cách **pop-art**, kiểu
game thành phố mở (lái xe, giao hàng, bị truy nã).

Kích thước 240x320, 15 FPS, heap 1024 KB, chipset MTK6260 (Nokia 220/225).

---

## Đọc phần này trước: "3D" ở đây nghĩa là gì

Đây là **pseudo-3D kiểu raycasting** (Wolfenstein 3D / Doom), **không phải 3D
thật**. Không phải vì lười — mà vì nền tảng MRE không cho phép:

| Thứ thường có ở 3D thật | Trên MRE 240x320 |
|---|---|
| GPU / tăng tốc đồ hoạ | **không có GPU** |
| Pha trộn alpha, khử răng cưa | **không có alpha** |
| Chiếu đa giác, kết cấu, z-buffer | **không có phép chiếu đa giác** |
| Hàm vẽ 1 điểm ảnh | **không có `pixel`, `vline`, `hline`** |

API thật chỉ có: `color clear rect frame line text image image_region set_font
text_width font_height flush tick_ms exit log capabilities device_info
runtime_compat` (`engine/src/runtime_bridge.c`). Mọi hình ở đây đều là **hình
chữ nhật đặc chồng lên nhau**.

Hệ quả trực tiếp, và cũng chính là thứ làm nên phong cách pop-art:

* **Không có alpha ⇒ không thể pha sương mù tại chỗ.** Màu tường vì vậy được
  **trộn trước** với màu khói thành 4 sắc độ (`popart.shade4`), rồi **chọn**
  theo khoảng cách. Đó là toàn bộ cơ chế "chiều sâu" của template này.
* **Không có `pixel` ⇒ "cột tường" là một `rect` rộng 4 px**, không phải vòng
  lặp từng điểm. Màn hình 240 px chia thành **60 cột × 4 px** — đúng chất
  "pixel rộng" của máy retro.
* **Không scale được chữ** ⇒ font firmware chỉ tới ~10 px. Chữ tiêu đề và số
  lớn phải tự vẽ bằng `rect` (`src/popart.lua`, font khối 3x5).

## Ngân sách khung hình (đo thật, không phải ước lượng)

`tools/popart_city_check.lua` đếm mọi lời gọi `rect` và cộng số điểm ảnh:

| Màn hình | Số `rect` / khung | Số điểm ảnh / khung |
|---|---|---|
| Tiêu đề | 337 | 146 489 |
| Đang chơi | **187** | **134 511** |

Ở 15 FPS, khung hình chơi ghi khoảng **2,0 triệu điểm ảnh/giây** — chưa bằng
một lần `clear()` toàn màn hình nhân đôi, nên còn dư địa.

Một chi tiết đáng nhớ: `l_rect` (`engine/src/runtime_bridge.c`) gọi thẳng
`ls30_fill` → `vm_graphic_fill_rect`, **một lời gọi firmware cho mỗi `rect`**.
Nếu firmware thiếu `fill_rect` thì `ls30_fill` rơi xuống bản dự phòng
`software_fill_from_line` — **một lời gọi cho MỖI DÒNG quét**, chậm hơn hẳn.
Trên giả lập `vm_graphic_fill_rect` có mặt (xem `emulator/mremu_debug.log`,
danh sách `sym miss` chỉ có `vm_log_*`).

## Bản đồ các tệp

```
main.lua            máy trạng thái màn hình + vòng chơi (tiêu đề/chơi/tạm dừng/hướng dẫn/wasted)
src/render.lua      renderer: trời, mặt trời, chân trời xa, sàn, tường DDA, sprite
src/popart.lua      bảng màu, trộn sắc độ theo khoảng cách, font khối 3x5, khung ô truyện
src/city.lua        thành phố dạng lưới, va chạm, danh sách vật thể
src/hud.lua         radar (bắc-up), mức truy nã, thanh HP/tốc độ, chip tên khu
src/player.lua      trạng thái người chơi/xe + hằng số vật lý (tách ra để test đọc được)
src/keypad.lua      hợp đồng phím S30+ (bản chuẩn, chép nguyên từ keypad-demo)
```

## Vòng chơi

Lái xe quanh thành phố, chạy vào **cột mốc vàng** để giao hàng: `+250$` mỗi
chuyến, **3 chuyến thì tăng một mức truy nã**. Đâm vào tường mất HP theo tốc độ;
hết HP thì hiện **WASTED** rồi chơi lại từ đầu.

Bản đồ sinh bằng **hàm băm tất định**, không dùng `math.random` — runtime chỉ
mở `base/table/string/math` (`engine/src/runtime_lua.c`), **không có `os`**, nên
không thể `math.randomseed(os.time())`. Thành phố vì vậy giống nhau mỗi lần
chạy; đó là chủ ý, để người học mở ra là thấy đúng thành phố như tài liệu.

Đường chiếm 2 ô đầu mỗi chu kỳ 5 ô, nên **tâm đường nằm ở toạ độ nguyên**
`1, 6, 11, 16, 21, 26, 31` (`city.LANE`). Điểm xuất phát và các cột mốc đều đặt
đúng tâm đường — lệch nửa ô là xe chỉ còn 0,16 ô mỗi bên và cạ ngay vào tường.

## Phím

Hợp đồng đầy đủ ở `doc/ai/Keypad.md`. Runtime **chỉ** gửi tên chữ thường.

| Phím | Lái xe | Đi bộ |
|---|---|---|
| `up` / `2` | tăng tốc | đi tới |
| `down` / `8` | phanh, lùi | đi lui |
| `left` `right` | lái (phải đang chạy mới ăn) | quay |
| `ok` / `5` | lên / xuống xe | lên / xuống xe |
| `softleft` / `softright` | tạm dừng | tạm dừng |
| `*` | đọc nhanh HP / tiền | đọc nhanh HP / tiền |

Hai điều dễ sai nhất:

1. **Runtime gửi lại `keypressed` khi giữ phím.** Hành động một lần (`ok`,
   softkey, `*`) **phải** chặn bằng cờ `fresh`; điều hướng thì để repeat cho
   cuộn nhanh. Thiếu chặn thì giữ `ok` là xe nhảy lên xuống liên tục.
2. **Lái xe cần một mức "bám" tối thiểu** (`grip = 0.35 + 0.65*|v|/2.5`). Xe
   thật phải chạy mới lái được, nhưng nếu để `grip` tỉ lệ thuần với tốc độ thì
   xe đứng yên không quay được chút nào — cạ vào tường là hết đường thoát.

## Build và kiểm chứng

Build VXP thật (chạy ở **foreground**):

```bash
python tools/build.py --project <đường-dẫn-project> \
  --toolchain toolchain/arm-gcc --compat-profile nokia225-rm1011 --no-run
```

Chạy harness logic (không cần toolchain, chỉ cần Lua 5.1):

```bash
cd templates/PopArtCity3D
<repo>/build/_lua51/lua.exe <repo>/tools/popart_city_check.lua
```

Harness dựng một bảng `engine` giả, **ghi lại mọi lời gọi `rect`/`text`** rồi
**raster hoá vào lưới 240x320**. Nhờ vậy nó kiểm được những thứ mà đọc code
không thấy:

* màn hình có bị **hổng** ở đâu không (mọi ô phải được tô),
* tường nằm đúng cột nào (đọc điểm ảnh đã vẽ),
* **sprite có bị tường che không** — so khung hình có/không có sprite,
* HUD có khớp trạng thái thật không (đọc thanh HP và chuỗi tiền đã vẽ),
* ngân sách `rect`/điểm ảnh mỗi khung,
* mọi màu vẽ ra đều thuộc bảng màu — **trên mọi màn hình**, không riêng màn chơi,
* **kiểu tham số** của mọi lời gọi `engine.*` khớp `runtime_bridge.c`,
* **không dòng chữ nào tràn ra ngoài 240 px**.

Hai phép kiểm tra cuối là để chặn hai lỗi thật đã mắc: `P.C.gold` không tồn tại
⇒ `E.text` nhận `nil` ở tham số #4 ⇒ runtime báo `bad argument #4` và chết cả
màn hình hướng dẫn; và dòng chữ dài quá 240 px bị cắt hai đầu. Cả hai đều **im
lặng** qua kiểm tra tĩnh. Chi tiết: `doc/studio/POPART_CITY_3D_1_0_2.md`.

Và `tools/validate_popart_city_template.py` canh phần tĩnh: ba chỗ đăng ký
template, appid không trùng, `src/keypad.lua` còn nguyên bản chuẩn, không dùng
`os`/`io`, không `pixel`/`vline`/`hline`, không tự `flush`, không cú pháp Lua
5.2+, và **mọi tên trong bảng màu (`P.C.*` / `HUD.C.*`) đều có thật**.

Cuối cùng, chạy thật trên emulator (cần toolchain ARM + MRE SDK + màn hình thật):

```bash
python tools/validate_popart_city_e2e.py
```

Script này build template, mở `VXPEmu.exe`, nhúng cửa sổ vào một widget 240x320
rồi **đọc pixel framebuffer** — vì `print()` của Lua không tới được log của
VXPEmu. Nó kiểm 6 dải trời, các sắc độ tường, dấu vết raycasting (các độ cao vỉa
hè khác nhau), lái xe làm đổi khung nhìn, đâm tường mất HP, bảng tạm dừng, màn
hình hướng dẫn, và **mép chữ không được chạm 2 px đầu/cuối màn hình**. Tự `SKIP`
nếu thiếu điều kiện.

Dự án ném để build nằm ở **temp của OS** (`%TEMP%/luas30_popart_e2e`), ảnh chụp ở
`build/_popart_e2e_shots/`. Đừng đổi dự án ném về `build/`: hook `[safe-delete]`
của host chặn `shutil.rmtree` khi vượt **ngân sách xoá theo lượt** (50 mục) và
thoát bằng `SystemExit(1)` — script chết với `exit 1` mà không in gì cả, trông y
như "E2E hỏng vì lý do khác". Chi tiết ở `doc/studio/POPART_CITY_3D_1_0_2.md` §6b.

## Muốn sửa thì sửa ở đâu

| Muốn đổi | Sửa ở |
|---|---|
| Thêm/bớt màu nhà, đổi độ cao | `popart.BUILD` (`r, g, b, hs`) |
| Đổi độ dày sương mù | `popart.SHADE_MIX` / `SHADE_DIM` |
| Đổi tầm nhìn, độ "thô" của cột | `render.M.FOV`, `render.M.COLS` (nhớ `COLS * COL_W = 240`) |
| Đổi độ cao đường chân trời | `render.M.HORIZON` |
| Đổi bố cục thành phố | `city.M.PERIOD`, `city.ROAD_W` |
| Đổi cảm giác lái | `player.FOOT_*`, `player.CAR_*` |
| Thêm loại vật thể mới | `render.SHAPE` + `render.META` + một mục trong `city.SPRITES` |

Hai bất biến dễ phá im lặng:

* **`COLS * COL_W` phải bằng bề ngang màn hình.** Lệch thì cột cuối bị hụt
  hoặc tràn, và `clip_ok` sẽ nuốt im lặng phần tràn.
* **Mọi màu vẽ ra phải nằm trong bảng màu.** Harness kiểm điều này (C8) nên gõ
  tay một mã hex giữa file là đỏ ngay.
