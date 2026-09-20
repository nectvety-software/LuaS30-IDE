CatBoxMRE v0.15.3 - MRE Manifest OOM Fix

Mục tiêu:
- Nokia 225 Dual SIM RM-1011 / MTK6260
- MediaTek MRE / LuaS30
- 240x320 / 15 FPS
- required_ram = 256 KB

Sửa quan trọng:
1. Thêm manifest.json ở ROOT project.
2. manifest.json dùng "required_ram": 256.
3. Đồng bộ 256 KB trong:
   - manifest.json
   - project.json
   - conf.lua
   - .luas30/mre_sdk.json
4. Giữ SafeBoot main.lua nhỏ, không image/atlas runtime.

Vì sao:
Các tool build MRE/VXP công khai dùng trường manifest "required_ram" để ghi mức RAM ứng dụng yêu cầu.
Nếu project chỉ có target_ram_kb/heap_kb nhưng packer không đọc các key đó, VXP có thể bị đóng gói
với RAM mặc định lớn hơn và điện thoại báo "not enough memory" trước khi Lua chạy.

Khi build bằng LuaS30 IDE:
- Xóa build/cache cũ nếu có.
- Mở đúng thư mục này (thư mục có manifest.json và main.lua).
- Clean/Rebuild.
- Kiểm tra build.log xem có "required_ram", "256", "262144" hoặc 0x40000.
