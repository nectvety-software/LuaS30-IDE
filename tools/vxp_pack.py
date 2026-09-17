"""
vxp_packer.py — Đóng gói .vxp thuần Python (tự phát triển, thay thế hoàn toàn
PackApp.exe của TinyMRESDK), format đã reverse-engineer byte-precise từ
PackApp output:

  .vxp = ELF(axf đã chèn section .vm_res) + TAGS + trailer 86 byte

ELF surgery (khớp PackApp):
  1. Đặt resource.bin (đã rebase mọi offset +vm_base) vào cuối file ELF
     như section mới `.vm_res` (SHT_PROGBITS=1, flags=0, addr=0).
  2. Mở rộng shstrtab: thêm tên ".vm_res" (copy shstrtab cũ sang chỗ mới,
     trỏ sh_offset của nó tới bản mới).
  3. e_shnum += 1; section header table dời xuống cuối (sau .vm_res);
     e_shoff cập nhật.
  4. Mọi offset trong resource name-table + id-table được cộng vm_base
     (= offset tuyệt đối của .vm_res trong file ELF mới) — MRE runtime
     (vm_res_init/vm_load_resource) đọc trực tiếp các offset này.

TAGS (giữ nguyên tập tag PackApp sinh, theo thứ tự quan sát được):
  0x01 vendor   0x02 app id   0x03 cert id   0x04 tên app
  0x05 version(0x100)   0x0F RAM KB   0x10 resolution (0 = any)
  0x11 engine version (0x9C400000, LE)   0x12 IMSI
  0x13 danh sách API/quyền: [code][1] x N, code = 5000 + chỉ số api_names
  0x16 1   0x18 0   0x19 tên app 3 ngôn ngữ   0x1C 0
  0x21 6 (= vxp build bằng GCC)   0x22 0   0x23 0   0x25 0   0x29 0
  0x00 END

Trailer 86 byte: marker B4 56 44 45 31 30 + LE32 cert_id + sig 64 byte
(**luôn để 0** — IDE không ký) + LE32 tags_pos + 8 byte 0.
"""
from __future__ import annotations

import struct
from pathlib import Path

TRAILER_SIZE = 86
MARKER = b"\xB4VDE10"

SHT_PROGBITS = 1
SHT_STRTAB = 3
SHDR_SIZE = 40
SHDR_FMT = "<IIIIIIIIII"  # name, type, flags, addr, offset, size, link, info, align, entsize


# ---------------------------------------------------------------- resource
def build_resource_bin(entries: list[tuple[str, bytes]]) -> bytes:
    """Gội [(tên, blob)] thành resource.bin (layout khớp fix_res_offsets PackApp).

    Layout: [name\\0 <ii off,len>]* , 00, <i id_table_pos>, [<Ii id,off abs>]*
    [FF FF FF FF, 0], blobs...  (offsets bản gốc — caller sẽ rebase).
    """
    names = [n for n, _ in entries]
    blobs = [b for _, b in entries]
    header_size = sum(len(n) + 1 + 8 for n in names) + 1 + 4
    id_table_size = 8 * (len(names) + 1)
    pos = header_size + id_table_size
    offsets = []
    for b in blobs:
        offsets.append(pos)
        pos += len(b)

    out = bytearray()
    for n, off, b in zip(names, offsets, blobs):
        out += n.encode("ascii", errors="replace") + b"\0"
        out += struct.pack("<ii", off, len(b))
    out += b"\0"
    id_table_pos = sum(len(n) + 1 + 8 for n in names) + 1
    out += struct.pack("<i", id_table_pos + 4)
    for i in range(len(names)):
        out += struct.pack("<Ii", i + 1, offsets[i])  # id bắt đầu từ 1 (khớp PackApp)
    out += struct.pack("<Ii", 0xFFFFFFFF, 0)
    for b in blobs:
        out += b
    return bytes(out)


def _rebase_resource(res: bytes, vm_base: int) -> bytes:
    """Cộng vm_base vào mọi offset trong name-table + id-table của resource.bin.

    Layout (khớp builder.gen_resource_bin / PackApp):
      [name\\0 <ii off,len>]*  ,  \\0 (sentinel 1 byte)
      <i id_pos_field>          (4 byte — vị trí id-table, cũng rebase)
      [<Ii idx, off>]*          (idx 1..n)
      <Ii 0xFFFFFFFF, vm_base>   (sentinel — off trỏ vm_base)
      blobs...
    """
    out = bytearray()
    pos = 0
    while True:
        end = res.find(b"\0", pos)
        if end < 0:
            raise ValueError("resource.bin hỏng: thiếu sentinel name-table")
        name = res[pos:end]
        if not name:
            # name rỗng = terminator name-table (1 byte 00) — giữ nguyên
            out += b"\0"
            pos = end + 1
            break
        pos = end + 1
        off, length = struct.unpack_from("<ii", res, pos)
        pos += 8
        out += name + b"\0"
        out += struct.pack("<ii", off + vm_base, length)
    # id_pos field (rebase)
    id_pos_field = struct.unpack_from("<i", res, pos)[0]
    out += struct.pack("<i", id_pos_field + vm_base)
    pos += 4
    # id entries: (idx, off) — off rebase
    while pos < len(res):
        idx, off = struct.unpack_from("<Ii", res, pos)
        pos += 8
        if idx == 0xFFFFFFFF:
            # sentinel: off trỏ về vm_base (đầu .vm_res) — khớp PackApp
            out += struct.pack("<Ii", idx, vm_base if off == 0 else off + vm_base)
            break
        out += struct.pack("<Ii", idx, off + vm_base)
    # blobs giữ nguyên
    out += res[pos:]
    return bytes(out)


# ---------------------------------------------------------------- ELF surgery
def _elf_add_vm_res(axf: bytes, resource: bytes) -> tuple[bytes, int]:
    """Chèn resource thành section `.vm_res` cuối ELF — byte-precise như PackApp.

    Layout PackApp (quan sát từ mini-farm.vxp):
      [axf nguyên bản NHƯNG shstrtab được mở rộng tại chỗ]
      shstrtab mở rộng = copy shstrtab cũ + b".vm_res\\0" (tại offset cũ của nó)
      [padding 4-align] [.vm_res = resource rebased]
      [padding 4-align] [section header table = 31 header cũ + 1 header .vm_res]
      ELF header: e_shoff -> bảng mới, e_shnum += 1, e_shstrndx giữ nguyên.

    Trả (elf_mới, vm_base).
    """
    if axf[:4] != b"\x7fELF":
        raise ValueError("axf không phải ELF")
    e_shoff, = struct.unpack_from("<I", axf, 0x20)
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", axf, 0x2E)

    secs = []
    for i in range(e_shnum):
        off = e_shoff + i * SHDR_SIZE
        secs.append(struct.unpack_from(SHDR_FMT, axf, off))

    shstr_off, shstr_size = secs[e_shstrndx][4], secs[e_shstrndx][5]
    shstr = bytearray(axf[shstr_off:shstr_off + shstr_size])
    vm_res_name_off = len(shstr)          # offset của ".vm_res" trong shstrtab mới
    shstr += b".vm_res\0"
    new_shstr_size = len(shstr)

    def align4(n: int) -> int:
        return (n + 3) & ~3

    # phần đầu ELF: giữ nguyên tới hết shstrtab CŨ, thay bằng shstrtab MỚI
    head = bytearray(axf[:shstr_off])
    head += shstr
    # .vm_res NGAY sau shstrtab — PackApp không align (0xc047b+0x134=0xc05af lẻ)
    vm_base = shstr_off + new_shstr_size
    head += _rebase_resource(resource, vm_base)

    # section table mới xuống cuối (align 4)
    new_shdr_off = align4(len(head))

    out = bytearray(head)
    out += b"\0" * (new_shdr_off - len(out))

    # header .vm_res (khớp PackApp): name_off, PROGBITS, flags=SHF_ALLOC(2),
    # addr=0, off, size, link=0, info=0, align=0, entsize=0
    vm_hdr = struct.pack(SHDR_FMT, vm_res_name_off, SHT_PROGBITS, 2, 0,
                         vm_base, len(resource), 0, 0, 0, 0)
    table = bytearray()
    for s in secs:
        name, stype, flags, addr, offset, size, link, info, align, entsize = s
        if stype == SHT_STRTAB and offset == shstr_off:
            # shstrtab: giữ offset cũ nhưng size mới
            table += struct.pack(SHDR_FMT, name, stype, flags, addr,
                                 shstr_off, new_shstr_size, link, info, align, entsize)
        else:
            table += struct.pack(SHDR_FMT, *s)
    table += vm_hdr
    out += table

    # cập nhật ELF header
    struct.pack_into("<I", out, 0x20, new_shdr_off)          # e_shoff
    struct.pack_into("<H", out, 0x30, e_shnum + 1)           # e_shnum
    # e_shstrndx giữ nguyên (shstrtab vẫn là section index cũ)

    return bytes(out), vm_base


# ---------------------------------------------------------------- tags build
# ------------------------------------------------------------- API / quyền
# tag 0x13 = VM_CE_INFO_PERMISSION ("system permission list", vmcert.h).
# Firmware dựng tập quyền của app từ danh sách này; app gọi API chưa khai sẽ
# bị báo lỗi quyền, và khai sai thì máy từ chối mở app.
#
# Định dạng: lặp [code:LE32][flag:LE32=1], code = 5000 + chỉ số trong api_names[].
# Nguồn đối chiếu (ground truth):
#   - XimikBoda/TinyMRESDK-main/PackApp/main.cpp: api_names[26] + api_names_to_vector()
#   - keystore/mre-sha-sdk/build.sh: API="File SIM_card ProMng" -> 5003/5007/5017,
#     khớp từng byte với keystore/HelloWorld/build/HelloWorld-s30.vxp.
MRE_API_BASE = 5000
MRE_API_NAMES = (
    "Audio", "Call", "Camera", "File", "HTTP", "Record", "Sensor", "SIM_card",
    "SMS_person", "SMS_SP", "TCP", "SysStorage", "Sec", "BitStream", "Contact",
    "LBS", "MMS", "ProMng", "SMSMng", "Video", "XML", "Payment", "SysFile",
    "BT", "UDP", "PUSH",
)
# Mặc định = mặc định của toolkit tham chiếu (keystore/mre-sha-sdk/build.sh).
MRE_API_DEFAULT = "File SIM_card ProMng"


def mre_api_codes(spec: str | None) -> list[int]:
    """Đổi chuỗi khai báo API (vd "Audio File ProMng") -> mã quyền.

    Khớp theo đúng ngữ nghĩa PackApp (``apis.find(api_names[i]) != npos``), tức
    khớp CHUỖI CON, không tách từ: "SysFile" cũng khớp "File". Giữ nguyên hành
    vi đó cho tương thích. Khoảng trắng và gạch dưới được coi như nhau nên cả
    "SIM card" lẫn "SIM_card" đều ra 5007.
    """
    norm = (spec or MRE_API_DEFAULT).replace("_", " ").lower()
    return [MRE_API_BASE + i for i, name in enumerate(MRE_API_NAMES)
            if name.replace("_", " ").lower() in norm]


def api_permission_blob(spec: str | None) -> bytes:
    """Payload của tag 0x13: [code][1] cho mỗi API được khai."""
    return b"".join(struct.pack("<II", code, 1) for code in mre_api_codes(spec))


def build_tags(app_name: str, vendor: str, app_id: int, ram_kb: int,
               api: str, elf_size: int) -> bytes:
    """Xây khối tags đúng tập + thứ tự PackApp quan sát được.

    tag 0x11 = hằng 0x9C400000 (engine version, quan sát mọi app PackApp build).
    tag 0x13 = danh sách API/quyền (xem api_permission_blob).
    tag 0x19 = [idx][len][tên] x3 — tên app 3 ngôn ngữ cho launcher.
    """
    def tag(t: int, v: bytes) -> bytes:
        return struct.pack("<II", t, len(v)) + v

    def text(s: str) -> bytes:
        return s.encode("utf-8") + b"\0"

    out = bytearray()
    out += tag(0x01, text(vendor))
    out += tag(0x02, struct.pack("<I", app_id))
    out += tag(0x03, struct.pack("<I", 1))          # cert id = 1 (dev, chưa ký)
    out += tag(0x04, text(app_name))
    out += tag(0x05, struct.pack("<I", 0x100))
    out += tag(0x0F, struct.pack("<I", ram_kb))
    out += tag(0x10, struct.pack("<I", 0))
    out += tag(0x11, bytes.fromhex("0000409C"))      # hằng PackApp
    out += tag(0x12, b"\x00")                        # IMSI trống (dev)
    # 0x13: danh sách API/quyền. Xem api_permission_blob + MRE_API_NAMES.
    out += tag(0x13, api_permission_blob(api))
    out += tag(0x16, struct.pack("<I", 1))
    out += tag(0x18, struct.pack("<I", 0))
    # 0x19: app list — [ [idx][len][name\0] x3 ] (idx 1,2,3 — khớp PackApp, không có count field)
    name_bytes = app_name.encode("utf-8") + b"\0"
    blob = b""
    for idx in (1, 2, 3):
        blob += struct.pack("<II", idx, len(name_bytes)) + name_bytes
    out += tag(0x19, blob)
    out += tag(0x1C, struct.pack("<I", 0))
    out += tag(0x21, struct.pack("<I", 6))
    out += tag(0x22, struct.pack("<I", 0))
    out += tag(0x23, struct.pack("<I", 0))
    out += tag(0x25, struct.pack("<I", 0))
    out += tag(0x29, struct.pack("<I", 0))
    out += tag(0x00, b"")                             # END
    return bytes(out)


# ---------------------------------------------------------------- entry points
def iter_elf32_symbols(axf: bytes):
    """Yield ELF32 symbol dictionaries from SHT_SYMTAB sections."""
    if len(axf) < 0x34 or axf[:4] != b"\x7fELF" or axf[4] != 1:
        return
    e_shoff, = struct.unpack_from("<I", axf, 0x20)
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", axf, 0x2E)
    if not e_shoff or e_shentsize < SHDR_SIZE:
        return
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        if off + SHDR_SIZE > len(axf):
            return
        name, stype, flags, addr, offset, size, link, info, align, entsize = \
            struct.unpack_from(SHDR_FMT, axf, off)
        if stype != 2 or not entsize:
            continue
        link_hdr = e_shoff + link * e_shentsize
        if link_hdr + SHDR_SIZE > len(axf):
            continue
        strtab_hdr = struct.unpack_from(SHDR_FMT, axf, link_hdr)
        strtab_off, strtab_size = strtab_hdr[4], strtab_hdr[5]
        strtab = axf[strtab_off:strtab_off + strtab_size]
        count = size // entsize
        for j in range(count):
            s_off = offset + j * entsize
            if s_off + 16 > len(axf):
                break
            st_name, st_value, st_size, st_info, st_other, st_shndx = \
                struct.unpack_from("<IIIBBH", axf, s_off)
            if st_name >= len(strtab):
                sym = ""
            else:
                end = strtab.find(b"\0", st_name)
                if end < 0:
                    end = len(strtab)
                sym = strtab[st_name:end].decode(errors="replace")
            yield {
                "name": sym,
                "value": st_value,
                "size": st_size,
                "info": st_info,
                "other": st_other,
                "shndx": st_shndx,
            }


def find_entry_offsets(axf: bytes, preferred_symbols: list[str] | None = None) -> list[int]:
    """Trả giá trị các symbol điểm vào, symbol của compiler được chọn lên đầu.

    Chỉ dùng cho chẩn đoán/kiểm tra — KHÔNG ghi vào tags. Loader MRE lấy điểm
    vào từ e_entry trong ELF header (xem ENTRY(gcc_entry) ở linker script).
    """
    preferred = preferred_symbols or [
        "gcc_entry", "rvct_entry", "ads_entry", "vm_main", "main"
    ]
    by_name = {}
    for symbol in iter_elf32_symbols(axf) or ():
        if symbol["name"] in preferred and symbol["shndx"] != 0:
            by_name.setdefault(symbol["name"], symbol["value"])
    values = [by_name[name] for name in preferred if name in by_name]
    if len(values) == 1:
        values.append(values[0])
    return values


# ---------------------------------------------------------------- pack
def pack_vxp(axf_path: Path, resource_entries: list[tuple[str, bytes]],
             app_name: str, vendor: str, app_id: int, ram_kb: int,
             api: str = MRE_API_DEFAULT) -> bytes:
    """Đóng gói .vxp HOÀN CHỈNH (chưa ký — sig zero). Trả bytes .vxp.

    Pipeline: ELF surgery (.vm_res) → tags → trailer (sig 0, cert 1).
    Đây là artifact cuối cùng: IDE không có bước ký nào tiếp theo.

    Điểm vào KHÔNG nằm trong tags: loader đọc e_entry từ ELF header, và
    ENTRY(gcc_entry) trong linker script quyết định giá trị đó.
    """
    axf = Path(axf_path).read_bytes()
    resource = build_resource_bin(resource_entries)
    elf, vm_base, = _elf_add_vm_res(axf, resource)

    tags = build_tags(app_name=app_name, vendor=vendor, app_id=app_id,
                      ram_kb=ram_kb, api=api, elf_size=len(elf))

    # trailer chưa ký: sig zero, cert_id=1, tags_pos
    tags_pos = len(elf)
    trailer = bytearray()
    trailer += MARKER
    trailer += struct.pack("<I", 1)      # cert id = 1 (dev)
    trailer += b"\0" * 64                 # sig zero
    trailer += struct.pack("<I", tags_pos)
    trailer += b"\0" * 8

    return elf + tags + bytes(trailer)
