# Vỏ máy giả lập — frame "classic dark" (1.0.2)

Tệp: `studio/app/widgets/vxp_emu_window.py`
Kiểm chứng: `tools/validate_emulator_shell_frame.py` (710 phép kiểm) +
`build/_rp_emulator_shell_frame.py` (36 ca phản chứng)
Mockup: `40689517_classic_dark-frame.png` (576×1288, RGBA)

## Vì sao phải viết lại

Cửa sổ giả lập trước đây là một cái khung có thanh công cụ: `PhoneWindowBar` +
`PhoneToolBar` với 7 nút, bàn phím 21 nút một dòng chữ, thân máy gradient chéo.
Người dùng yêu cầu UI lại theo mockup "classic dark".

Điểm mấu chốt khiến việc này khó kiểm chứng: **thân máy không dùng QSS**. Mọi thứ
(gradient, rail công cụ, bong bóng tên, hàng trạng thái, bàn phím hai dòng) do
`paintEvent` vẽ tay. Đổi một hằng số là vỏ máy lệch khỏi mockup mà **không có lỗi,
không có cảnh báo, không có test nào đỏ**. Nên cách duy nhất để canh nó là render
thật rồi soi điểm ảnh — đó là toàn bộ lý do `validate_emulator_shell_frame.py`
tồn tại.

## Mockup là nguồn số đo

Mockup **đúng 2× vỏ thật**: màn hình của nó là 480×640 px, tức 2× framebuffer
240×320; thân vỏ 536 px = 2× 268. Nên mọi số dưới đây là px THẬT = số đo mockup
chia 2.

Cách đo: **chế độ (mode) của từng vùng**, không lấy một điểm ảnh đơn lẻ — điểm
đơn lẻ hay trúng nét chữ. Ngoài ra ảnh PNG có kênh alpha và **có bóng đổ**, nên
mép thiết bị phải tìm bằng viền ngoài `#435069` chứ không bằng hộp alpha.

| Hạng mục | Giá trị (px thật) |
| --- | --- |
| Thân vỏ | 268 × 604, bo góc 18, viền `#435069` 1.5px |
| Gradient thân | dựng đứng `#2a3343` → `#161d28` |
| Màn hình | (14, 34) 240×320 |
| Bàn phím | (17, 366) 234×232 |
| Phím | 76 rộng, khe ngang 3, khe dọc 4 |
| Chiều cao hàng | 26 (điều hướng) · 36 (OK) · 30 (số) |
| Phím | nền `#34445d`, viền `#506685`, bo 10 |
| Chữ trên phím | số `#ffffff` 14px đậm · chữ nhỏ `#9aa6b8` 9px |
| Chip nổi (đã bỏ) | cao 32, chờm xuống đỉnh vỏ 5, cách mép 6 |
| Rail công cụ | rộng 34, nút icon 30 vuông, khe dọc 4, lề trên/dưới 10, khe với thân máy 8 |
| Bong bóng tên | cao 24, đệm ngang 8, khe với rail 6, bo 6 |
| Thanh tín hiệu | 15×5, tâm y 13.5; dòng khung hình tâm y 25 |
| Nhấn | `#65dc96` |

## Bảng màu là màu THIẾT BỊ, không phải chrome IDE

`tools/studio_theme_check.py` cấm hex ngoài `palette.py`, và
`app/widgets/vxp_emu_window.py` nằm trong `ALLOWLIST` với lý do "ART THIẾT BỊ".
Đây đúng là ngoại lệ đó: màu vỏ máy **không** theo palette IDE, giống
`items.C_ACCENT` của game. Khối hằng số ở đầu tệp ghi rõ điều này, và validator
kiểm chính câu ghi chú đó còn đó (`"THIẾT BỊ" in SOURCE`).

## Chỗ PHẢI bịa thì chọn nói thật

Mockup có `4G VoLTE`, `WiFi · 1.0Gbps`, `56 FPS`, `Menu`/`Contacts`, và đồng hồ
`10:30` / `Mon 12 May`. **App không có nguồn dữ liệu nào cho những số đó** — đã
kiểm: không chỗ nào trong `EmulatorService` hay shell đo FPS, không có dữ liệu
mạng. Chép nguyên vào là bịa số. Nên:

| Mockup | Thay bằng | Nguồn |
| --- | --- | --- |
| `4G VoLTE` + vạch sóng | tên tệp `.vxp` đang nạp + nhãn trạng thái | `ScreenHost.name` / `state` |
| `10:30` / `Mon 12 May` | giờ + ngày **thật**, cập nhật mỗi 20s | `QDateTime` + `QLocale.system()` |
| `WiFi · 1.0Gbps` | `VXPEmu · PID <pid>` hoặc `VXPEmu · chưa nối` | `native_window.find_main_window` |
| `56 FPS` | `240×320 · 15 FPS` — **mục tiêu**, không phải số đo | `conf.lua` của `templates/*` |
| `CLASSIC DUAL SIM` | `NOKIA 225 DUAL SIM` | model thật của vỏ máy |
| `Menu` / `Contacts` | `Menu` / `Chọn` | hai phím mềm thật của máy |

Thanh tín hiệu màu xanh chỉ khi **đã nhúng được cửa sổ VXPEmu**; chưa nối thì
xám `#5b6472`. Nó là chỉ báo thật, không phải hoạ tiết.

## Bàn phím: 21 phím, không phải 18

Mockup vẽ **18** phím (cụm điều hướng 6 + 12 phím số). Hợp đồng phím của dự án
(`doc/ai/Keypad.md` §0, canh bởi `validate_keypad_emulation.py`) bắt buộc **21**.
Giữ đúng hình dáng mockup và nhét đủ 21 phím:

```
        ☰        ↑        ✕          hàng 1 (26)
        ‹        OK       ›          hàng 2 (36 — OK cao hơn)
      Back       ↓      Clear        hàng 3 (26)
      1/∞   2/abc  3/def             hàng 4-7 (30)
      4/ghi 5/jkl  6/mno
      7/pqrs 8/tuv 9/wxyz
      */+    0/–    #/Aa
```

Hai quyết định có lý do:

- **`back` và `clear` dùng CHỮ, không dùng glyph.** Glyph `back` của bộ icon là
  một mũi tên trái; đứng cạnh `left` (cũng mũi tên trái) thì không ai phân biệt
  được nút nào là nút nào — mà đây là nút để bấm. `Back`/`Clear` làm hàng 3 đối
  xứng với hàng 1 (glyph–glyph–glyph) và hàng 2 (glyph–OK–glyph).
- **`⇧` không dùng được.** `⇧` (U+21E7) **không có trong `segoeui.ttf`** — chỉ
  Segoe UI Symbol mới có — nên vẽ bằng Segoe UI là ra ô vuông, im lặng. Đổi
  thành `Aa`, vừa là ASCII vừa là ký hiệu shift thật. `∞` (U+221E) và `–`
  (U+2013) thì Segoe UI có, giữ nguyên.

`#` bị **làm mờ chữ** (opacity 0.45) vì `native_window.MRE_KEYS_NOT_INJECTABLE`
chặn nó: bấm không có gì xảy ra. Làm mờ để sự thật đó NHÌN thấy được thay vì chỉ
nằm trong tooltip.

## Rê chuột lên phím: tên phím hiện NGAY TRÊN VỎ MÁY

Yêu cầu: "khi dê chuột sẽ hiện tên của các nút bấm". `setToolTip()` đã có từ
trước (đủ 21 phím + 7 icon rail), nhưng tooltip **không phải chỗ đáng tin**:

- nó là cửa sổ của hệ điều hành — trễ ~700ms, có thể bị cửa sổ khác che, và
  **không kiểm chứng được offscreen** (xem mục bẫy số 10);
- tên phím (`up`, `softleft`, `#`) là thứ người dùng cần thấy NGAY khi trỏ vào,
  vì trên mặt phím không có chữ nào nói lên tên đó.

Nên tên phím được vẽ vào **dòng dưới của hàng trạng thái** — vị trí luôn nhìn
thấy, kể cả khi VXPEmu đang chạy chiếm màn hình:

```
  ▬ VXPEmu · PID 4321        <- dòng 1: kết nối (không đổi)
      2 · abc               <- dòng 2: tên phím khi rê chuột (chữ SÁNG)
   240×320 · 15 FPS         <- dòng 2 khi không rê chuột (màu nhấn xanh)
```

Kèm theo, phím đang trỏ **sáng lên** (`KEY_FILL_HOVER`) để biết tên đó ứng với
phím nào. Hai màu khác nhau cho hai trạng thái của dòng 2 là cố ý: cùng màu thì
không ai nhận ra dòng đó vừa đổi nội dung.

`KEY_FILL_HOVER = "#3f5580"` là màu **SUY RA**, không lấy từ mockup — mockup
không có trạng thái hover. Nó phải đủ xa `KEY_FILL` (`#34445d`) để nhìn ra và đủ
xa `KEY_FILL_HELD` (`#4e6c96`) để không lẫn với "đang giữ"; validator canh đúng
khoảng cách đó.

Chuỗi hiện ra là **tên Lua** trong `doc/ai/Keypad.md` §0, thêm chữ nhỏ nếu phím
có (`2 · abc`, `# · Aa`, `* · +`). Tooltip vẫn giữ nguyên để có thêm phần mô tả
dài. Tên lấy từ `PhoneKeypad.MRE_KEY_NAMES` — cùng nguồn với tooltip, nên hai
chỗ không thể lệch.

## Rail icon bên phải thay hai chip (và bỏ luôn `QMenu`)

Yêu cầu: *"các menu của giả lập VXPEmu chuyển sang phải như máy ảo LDPlayer 14 chỉ
icon khi dê chuột và sẽ hiện title lên"*.

Bản trước là hai chip `MENU`/`Shot` chờm lên đỉnh vỏ; `MENU` mở một `QMenu` chứa
đủ 7 việc (chạy/dừng, nạp `.vxp`, chụp màn hình, mở thư mục ảnh, quay video, xoay,
toàn màn hình). Nay là `ToolRail` dọc **bên phải** thân máy, **chỉ icon**, và tên
công cụ hiện trong **bong bóng** khi rê chuột. Không mất chức năng nào — 7 khoá
`RAIL_ITEMS` phải khớp đúng 7 khoá `_tool_handlers()`.

Rail và bong bóng nằm **ngoài** khung `PhoneBody` nên không thể là con của nó —
đó là lý do tồn tại của `PhoneStage`. Thân máy giờ ở `(0, 0)` (bản chip đẩy nó
xuống `CHIP_H - CHIP_OVERLAP`), nên `stage.width() != body.width()` và mọi toạ độ
trong ảnh `stage.grab()` đã dịch so với bản cũ.

Ba quyết định, đều có lý do đo được:

- **Bong bóng tự vẽ (`RailTip`), KHÔNG dùng `QToolTip`.** Tooltip không kiểm
  chứng được offscreen (bẫy số 8) — xây tính năng dựa vào thứ không đo được thì
  không guard nào bảo vệ nó. Bong bóng là widget thật, soi được bằng điểm ảnh.
- **Bong bóng phải mang `WA_TransparentForMouseEvents` và phải là widget LÁ.**
  Nó vẽ đè lên mép phải thân máy — chỗ có bàn phím cần bấm. Cờ này áp cho cả
  widget lẫn con, nên `RailTip` không được chứa nút.
- **Bỏ `QMenu` là bỏ một bẫy.** `QMenu.exec()` mở vòng lặp sự kiện **LỒNG NHAU**,
  validator offscreen bấm vào sẽ treo im lặng. Đổi lại, `_choose_vxp` mở
  `QFileDialog` (modal) và `open_capture_folder` mở trình duyệt tệp của OS — nên
  §E3 vẫn phải bấm trên một `PhoneStage` **riêng**, không bấm rail của cửa sổ thật.

Icon đổi hình theo **trạng thái thật** (`_sync_rail()`): `play`↔`stop`,
`circle`↔`stop`, `expand`↔`collapse`, kèm viền `ACCENT` khi công cụ đó đang bật.
Bỏ sót một chỗ gọi `_sync_rail()` là rail **nói dối** (vẫn vẽ "play" trong khi
giả lập đang chạy) — validator canh sự có mặt của lời gọi trong cả năm hàm đổi
trạng thái.

## Bẫy

### Trong widget

- `setGeometry()` **không nhận cha**. Bản đầu tôi tạo `PhoneKey(...)` không
  truyền `parent`; 21 nút thành cửa sổ rời và bàn phím trống trơn, không lỗi,
  không log. Phải là `PhoneKey(..., self)`.
- `live` phải **suy ra** từ `state` (`ScreenHost.set_state`), không đặt rời.
  Hai cờ cùng nói một chuyện thì sớm muộn cũng lệch — mà lệch ở đây nghĩa là vẽ
  đè lên cửa sổ VXPEmu đang chạy.
- Đồng hồ màn hình chờ dùng `QTimer` 20s và **chỉ `update()` khi không live**.
- `PhoneRailButton`/`PhoneKey` đều `NoFocus`: nếu không, phím mũi tên bị Qt dùng
  để chuyển focus và không tới được cửa sổ giả lập.
- **Bong bóng `RailTip` và rail đặt bằng hai hệ toạ độ khác nhau.**
  `ToolRail._on_hover` phát tâm Y của nút, nhưng `button.y()` là toạ độ TRONG
  rail còn `PhoneStage._on_rail_hover` đặt bong bóng bằng toạ độ TRONG stage —
  phải cộng `self.y()` (đã mắc: bong bóng hiện cao hơn nút ~175px, **không lỗi,
  không cảnh báo**).

### Trong validator (đã mắc thật, đừng "đơn giản hoá" lại)

1. **`QWidget.grab()` tô vùng chưa vẽ bằng `#efefef`**, không phải nền vỏ máy.
   Nên "đếm điểm ảnh khác nền" không chứng minh gì: bàn phím KHÔNG hề vẽ cũng ra
   đầy "mực" và phép kiểm xanh. Phải đếm điểm ảnh **trùng màu X**.
2. **Gốc toạ độ là `PhoneStage`, và stage RỘNG HƠN thân vỏ.** Thân vỏ ở `(0, 0)`,
   nhưng rail nằm bên phải nó ⇒ `stage.width() == body.width() + RAIL_GAP_X +
   RAIL_W`, và `stage.width() != body.width()`. Bản chip thì ngược lại: thân vỏ bị
   đẩy xuống `CHIP_H - CHIP_OVERLAP`, nên "(1,1)" là vùng trống phía trên chip và
   phép kiểm góc bo xanh vô điều kiện. Tương tự: toạ độ nút là toạ độ TRONG
   `PhoneKeypad`, phải cộng lề ngang 17px của nó; toạ độ nút rail là toạ độ TRONG
   `ToolRail`, phải cộng `rail.geometry().topLeft()`.
3. **Widget modal/dialog là đường treo offscreen.** `QMenu.exec()` là vòng lặp sự
   kiện LỒNG NHAU (nay đã bỏ hẳn, và validator cấm nó quay lại). Nhưng
   `QFileDialog` (`_choose_vxp`) và trình duyệt tệp của OS (`open_capture_folder`)
   cũng vậy: bấm rail của cửa sổ THẬT trong script nền sẽ treo hoặc bật cửa sổ lạ.
   Phải dựng một `PhoneStage` riêng để kiểm hành vi phát tín hiệu của rail.
4. **So cả ảnh màn hình chờ để kiểm "đồng hồ là giờ thật" là vô nghĩa**: dòng
   NGÀY cũng đổi theo giờ nên phép thử vẫn xanh dù đồng hồ đã bị hard-code. Phải
   so ĐÚNG dải đồng hồ (`copy(CLOCK_BAND)`).
5. **Gradient chéo vs dựng đứng không phân biệt được ở orientation DỌC**: thân vỏ
   268×604 nên đường chéo bị trục y chi phối, hai mép cùng hàng chỉ lệch ~3 đơn
   vị màu. Phép thử có răng phải chạy ở **NGANG** (594×280).
6. **Đừng lấy mẫu ở `x=0` / `x=width-1`**: đó là nét viền, cùng một màu ở mọi
   hàng, nên "hai mép cùng hàng phải cùng màu" xanh vô điều kiện.
7. **Đừng kiểm tỉ lệ điểm ảnh trùng nền phím trên cả hình chữ nhật trong của
   phím**: phím bo góc 10px nên bốn góc của hình đó nằm ngoài hình vẽ và bị khử
   răng cưa, kéo tỉ lệ xuống 65-72%. Lấy MỘT điểm chắc chắn trong lòng phím, và
   lấy DẢI GIỮA (cách mép 9px, cách trên/dưới 4px) để đếm mực chữ.
8. **Đừng lấy "tooltip có hiện không" làm phép kiểm.** `QTest.mouseMove()` rồi
   đọc `QToolTip.isVisible()`/`QToolTip.text()` **luôn** ra "không hiện" — kể cả
   với một `QPushButton` thường có tooltip, tức là phép đo vô hiệu chứ không phải
   app lỗi (đã chạy đối chứng để biết điều này). Chụp màn hình thật với chuột
   thật cũng không kết luận được: cửa sổ khác che mất. Kết luận rút ra không phải
   "tooltip hỏng" mà là **đừng xây tính năng dựa vào thứ không đo được** — hãy vẽ
   vào widget để soi được bằng điểm ảnh.
9. **Hai dòng của hàng trạng thái có hộp chữ CHỒNG nhau**: dòng 1 là 5.5–21.5,
   dòng 2 là 17–33 (cùng hệ toạ độ thân vỏ). Đo nửa dưới hộp dòng 2 (25–33) thì
   `* · +` mất sạch mực (`*` nằm cao, `+` nằm giữa) ⇒ đỏ vô cớ; đo cả hộp thì lẫn
   chữ dòng trên, mà dòng trên vẽ đúng bằng `ACCENT` ⇒ phép "dòng khung hình đã
   biến mất" đỏ vô cớ. Cách đúng: đo **cả hộp** cho mực TRẮNG (dòng trên không
   bao giờ vẽ màu gần trắng, xem `HOVER_BAND`/`FRAME_BOX`), và chứng minh dòng
   khung hình biến mất bằng cách **so LƯỢNG mực xanh trước/sau** — mực xanh của
   dòng trên là hằng số ở cả hai lần đo nên hiệu cô lập đúng dòng dưới.
10. **Trộn hai hệ toạ độ**: `FRAME_Y` và `BODY_DY` đã ở hệ ảnh `stage.grab()`,
    còn `shell.SCREEN_TOP` thì chưa. Trộn vào nhau ra `QRect(0, 52, 268, -18)` —
    chiều cao ÂM, và mọi phép đếm trong đó trả 0 mà không báo lỗi. Phải có
    `SCREEN_TOP_STAGE = BODY_DY + shell.SCREEN_TOP`.
11. **Ngưỡng mực sáng phải tính tới tên phím NGẮN NHẤT.** `* · +` ở cỡ 13px chỉ ra
    ~17 điểm mực sáng; ngưỡng 20 làm đúng chuỗi đó đỏ vô cớ. Ngưỡng 10 vẫn phân
    biệt được với "không vẽ gì" (0 điểm).
12. **Thứ tự `Enter`/`Leave` giữa hai nút kề KHÔNG được Qt bảo đảm.** Xử lý theo
    cặp ("Enter thì bật, Leave thì tắt") làm tên phím tắt ngay sau khi vừa bật —
    nhưng chỉ ở MỘT trong hai thứ tự, nên rất khó thấy. Đúng: nhớ nút MỚI NHẤT
    được Enter, và chỉ xoá khi CHÍNH nút đang nhớ phát Leave. **Đúng y như vậy ở
    rail** (`ToolRail._on_hover`), chỉ khác là ở rail thì bong bóng SAI VỊ TRÍ chứ
    không chỉ sai chữ, nên còn khó thấy hơn.
13. **`hideEvent` là đường duy nhất dọn hover.** Nút bị ẩn lúc đang rê chuột thì
    `leaveEvent` không tới nữa, và tên phím **kẹt lại vĩnh viễn** trên hàng trạng
    thái — y như `release_held()` trong `hideEvent` chống kẹt phím đang giữ. Ở rail
    hậu quả là bong bóng **kẹt vĩnh viễn** trên màn hình (`rail.hide()` phải tắt nó).
14. **`childAt()` TÔN TRỌNG `WA_TransparentForMouseEvents` — đã đo, không suy
    đoán.** Nên "bong bóng không chặn chuột" chứng minh được bằng
    `stage.childAt(tâm_bong_bóng)`: trả về `ScreenHost`, không phải `RailTip`. Chỉ
    kiểm cờ bằng `testAttribute()` là chưa đủ (cờ có thể đặt lên nhầm widget);
    phải kiểm CẢ HAI.
15. **Viền accent 1px phải đếm CẢ Ô, đừng dò một điểm.** `drawRoundedRect` vẽ viền
    lệch nửa điểm ảnh và bốn góc bo nằm NGOÀI hình vẽ (bị `grab()` tô `#efefef`),
    nên `at(left + 1, giữa)` trả về màu NỀN ⇒ đỏ oan. Đo được: bật ⇒ 88 điểm,
    tắt ⇒ 0; ngưỡng 40.

### Trong harness phản chứng

16. **Tệp nguồn dùng CRLF.** Mẫu cần phá mà kết thúc bằng `\n` chỉ khớp phần `\n`,
    để lại `\r` + thụt lề cũ ⇒ `IndentationError`. Ca phản chứng khi đó "đỏ vì lý
    do khác" trong khi thật ra chỉ đỏ vì vỡ cú pháp. Mẫu không chứa `\n`, hoặc
    `_replace()` phải thử cả hai kiểu xuống dòng; và harness phải **từ chối** ca
    đỏ có `Traceback`/`SyntaxError`/`IndentationError`.
17. Sao lưu theo **từng tệp** và chỉ lấy bản GỐC (`backups.setdefault`).
18. **Mẫu phá phải cập nhật khi chữ ký hàm đổi.** Thêm tham số `readout` vào
    `PhoneKey(...)` làm ca "nút không nhận cha" mất mẫu (`không tìm thấy mẫu cần
    phá`). Harness báo đúng như vậy — nhưng nếu nó im lặng bỏ qua ca đó thì một
    guard đã mất răng mà không ai biết. Đừng bao giờ để "không tìm thấy mẫu"
    thành cảnh báo suông.
19. **Mẫu phá phải DUY NHẤT trong tệp — `_replace()` thay lần khớp ĐẦU TIÊN.**
    `PhoneKey.enterEvent` và `PhoneRailButton.enterEvent` có thân y hệt nhau
    (`self.hover_changed.emit(self, True)`), mà `PhoneKey` khai TRƯỚC. Ca "rail
    thôi báo hover" dùng mẫu ngắn sẽ phá **bàn phím**, validator vẫn đỏ — nhưng đỏ
    ở §F, tức ca phản chứng "đỏ vì lý do khác" mà trông vẫn như đạt nếu ai đó chỉ
    liếc kết quả. Phải neo vào dòng comment chỉ rail mới có. Cùng họ với bẫy
    "guard chứa chính token nó cấm".
20. **Đừng phá bằng cách đổi TÊN hàm/hằng còn được gọi ở nơi khác.** Ca "_sync_rail
    bị bỏ sót" không được đổi tên `_sync_rail` (⇒ `AttributeError` khi dựng
    `window`, harness thấy `Traceback` và xếp vào "đỏ vì vỡ cú pháp"), mà phải XOÁ
    đúng một lời gọi trong `process_stopped`.

## Phản chứng

`build/_rp_emulator_shell_frame.py` — **36 ca**, mỗi ca phá đúng một hành vi rồi
chạy lại validator: phải ĐỎ, đỏ vì **đúng lý do**, và xanh lại sau khi khôi phục.
Kết quả: **36/36**.

Bao gồm cả những ca mà bản đầu của validator đã xanh vô ích: bỏ `parent=self`,
đổi gradient sang chéo, hard-code đồng hồ, `BODY_RADIUS = 0`, và đổi `Aa` lại
thành `⇧`. Tám ca cho tính năng rê chuột bàn phím: thôi phát tên, thôi nối tín
hiệu, `Leave` không tắt, **xử lý hover theo cặp**, thôi sáng phím, màu hover quá
gần nền, ẩn bàn phím để tên phím kẹt, và tên phím chứa ký tự Segoe UI không có.
Mười hai ca cho rail + bong bóng: khe âm (rail đè thân máy), rail hẹp hơn icon,
thôi canh giữa dọc, mất một chức năng, icon mất tên, thôi vẽ viền accent,
`_sync_rail()` bỏ sót ở `process_stopped`, thôi phát tín hiệu bấm, thôi nối tới bộ
dispatch, thôi báo hover, **quên cộng `rail.y()`** (lệch hệ toạ độ), rời icon mà
bong bóng không tắt, bỏ `WA_TransparentForMouseEvents`, và ẩn rail để bong bóng kẹt.

Ba ca trong số đó chỉ có răng nhờ **đo**, không nhờ đọc code: lệch hệ toạ độ
(`rail.y()`), cờ trong suốt chuột (`childAt`), và viền accent (đếm cả ô).

## Việc còn lại

- Chưa có FPS đo được, nên hàng trạng thái chỉ dám ghi FPS **mục tiêu**. Muốn có
  số đo thật thì phải bổ sung nguồn ở `EmulatorService`, không phải bịa ở đây.
- **Bong bóng tên công cụ là widget thật, không dùng `QToolTip`.** Rail chỉ có
  icon nên tên là thứ BẮT BUỘC phải có — nếu sau này muốn thêm mô tả dài hơn thì
  đừng quay lại tooltip (bẫy số 8); hãy vẽ thêm, hoặc nối vào hàng trạng thái như
  `PhoneBody.set_hover` của bàn phím.
- **Bàn phím và rail dùng hai kênh hiện tên khác nhau** (hàng trạng thái vs bong
  bóng). Cố ý: bàn phím có 21 phím nằm trong lòng thân máy, hiện tên ngay trên vỏ
  là chỗ luôn nhìn thấy; rail nằm NGOÀI thân máy nên không có chỗ nào để vẽ.
  Thống nhất chúng thành một kênh là việc còn lại nếu thấy cần.
- Nút đóng/mở cửa sổ vẫn là chrome hệ thống (đúng chủ ý: cửa sổ giả lập là ngoại
  lệ của chuẩn frameless — xem `doc/studio/MODAL_TITLEBAR_1_0_1.md`).
- Nếu sau này cần `#` gửi được vào VXPEmu thì phải sửa **VXPEmu** để có đường
  inject mã MRE trực tiếp, không phải sửa shell.
