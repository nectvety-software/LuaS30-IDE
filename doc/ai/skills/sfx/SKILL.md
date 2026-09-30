---
name: sfx
description: Tao hieu ung am thanh SFX cho game/app LuaS30 bang engine headless kawaiiak (VOICES/buildWav, WAV PCM16 16kHz): recipe LayerSpec, script make_*_sfx.ts, nap qua engine.audio_play, verify bang build + emulator
---

# SFX cho LuaS30 (engine kawaiiak)

Dùng skill này khi game/app LuaS30 cần tiếng nhảy, bắn, nhặt đồ, click menu,
thắng/thua... mà không thu âm thật. Sinh bằng synth headless của kawaiiak
(`D:\noolechi\kawaiiak/src/8bit/sfxEngine.ts` — DSP TypeScript thuần, không
Web Audio/DOM/FFmpeg, chạy ngay trong Node), rồi nạp file WAV vào project.

## Công thức âm (LayerSpec)

Mỗi SFX = một `SfxSpec {name, layers[], peakTarget?}`, mỗi layer:

```text
t0 (giây bắt đầu) · gate (giữ) · attack · peak · release
osc: sine | square | saw | tri | noise
f0 (Hz, noise = hệ số scale băng thông) · f1/glideTime (glide mũ)
filter {lowpass|highpass|bandpass, f0, f1?, q} · detune (cents) · level
```

Entry nhanh: `VOICES.chime(freq, t0, gate, opts)` (opts ghi đè
peak/attack/release/f1/filter/level). Các giọng sẵn:
`chime lead bass lofi house pad asmr kick snare clap hat`.
Tần số từ nốt: `midiToFrequency(60)` = C4 261.6 Hz.
Chuỗi master: DC-block → tanh limiter → hạ mẫu 48 kHz → 16 kHz (`TARGET_RATE`)
sinc Kaiser → normalize → `encodeWav()` = PCM16 mono header 44 byte.
Noise dùng PRNG theo seed → cùng seed ra cùng bytes (so được giữa các build).

## Script sinh (mẫu make_fnynn_sfx.ts)

Viết `scripts/make_<game>_sfx.ts` trong repo kawaiiak (chạy `npx tsx`):

```text
npx tsx scripts/make_<game>_sfx.ts --out <project>/assets/sfx --review <dir-ngoai-assets>
npx tsx scripts/make_<game>_sfx.ts --only hit,coin   (render thử vài id)
```

- Định nghĩa công thức khớp đúng danh sách tên sfx của game.
- `--out` = thư mục asset game (WAV 16 kHz vào đây để build đóng vào VXP).
- `--review` = thư mục RIÊNG ngoài assets: mix preview + manifest JSON
  (bytes/seconds/`len_ms`/peak/rms/zcr). Tách riêng vì pipeline game glob
  mọi `*.wav` trong assets — file preview lạc chỗ sẽ phình bản phát hành.
- `len_ms` (làm tròn lên +10% dư) là giá trị nạp vào bảng guard chống dồn
  tiếng phía game.

## Nạp vào LuaS30 (engine.*)

```lua
if engine.has_audio then
    engine.audio_play("assets/sfx/hit.wav")
end
```

- Chỉ dùng `engine.audio_play/stop` + `has_audio`; firmware/codec khác theo
  thiết bị nên mọi tiếng đều phải optional (game vẫn chơi khi câm).
- `audio_set_volume(0)` = mute (thang 0..6). Không phát chồng vô hạn: giữ
  bảng `len_ms` từ manifest, bỏ qua trigger khi tiếng còn vang.
- WAV ngắn (< 1s), mono, 16 kHz — hợp heap 1 MB và RAM profile thiết bị.

## Definition of done (nghe + đo, không nói suông)

- Manifest đủ cho mọi id: bytes/seconds/`len_ms`/peak/rms/zcr hợp lý
  (peak < 1.0 sau normalize, seconds khớp thiết kế).
- Nghe thật file preview: đúng giọng, không rè/clip, độ dài đúng.
- Determinism: chạy script 2 lần — WAV byte-identical.
- Trong engine: 1 tiếng phát đúng lúc + 1 tiếng bị guard chặn khi dồn +
  mute hoạt động. Build VXP (`tools/build.py`) PASS rồi smoke trên emulator.
