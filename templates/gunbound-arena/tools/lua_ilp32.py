# Convert Lua 5.1 bytecode compiled by an x64 luac (sizeof(size_t)=8)
# into ILP32 bytecode (sizeof(size_t)=4) for the 32-bit ARM MRE runtime.
# Only size_t fields (string lengths) and the header byte differ.
import struct
import sys


class Reader:
    def __init__(self, buf):
        self.buf = buf
        self.pos = 0

    def take(self, n):
        if self.pos + n > len(self.buf):
            raise ValueError("unexpected end of bytecode at %d" % self.pos)
        b = self.buf[self.pos:self.pos + n]
        self.pos += n
        return b

    def u8(self):
        return self.take(1)[0]

    def i32(self):
        v, = struct.unpack("<i", self.take(4))
        if v < 0 or v > 0x7FFFFFFF:
            raise ValueError("bad int %d" % v)
        return v

    def size(self, size_t):
        if size_t == 8:
            v, = struct.unpack("<Q", self.take(8))
        else:
            v, = struct.unpack("<I", self.take(4))
        if v > 0x7FFFFFFF:
            raise ValueError("bad size %d" % v)
        return v


class Writer:
    def __init__(self):
        self.out = bytearray()

    def raw(self, b):
        self.out += b

    def u8(self, v):
        self.out.append(v)

    def i32(self, v):
        self.out += struct.pack("<i", v)

    def size(self, v):
        self.out += struct.pack("<I", v)


def parse_proto(rd, wr, size_t):
    # source string
    n = rd.size(size_t)
    if n == 0:
        wr.size(0)
    else:
        s = rd.take(n)
        wr.size(len(s))
        wr.raw(s)
    wr.i32(rd.i32())                      # linedefined
    wr.i32(rd.i32())                      # lastlinedefined
    for _ in range(4):                    # nups numparams is_vararg maxstacksize
        wr.u8(rd.u8())
    ncode = rd.i32()
    wr.i32(ncode)
    wr.raw(rd.take(ncode * 4))            # instructions: 4 bytes on both
    nk = rd.i32()
    wr.i32(nk)
    for _ in range(nk):
        t = rd.u8()
        wr.u8(t)
        if t == 0:                        # nil
            pass
        elif t == 1:                      # boolean
            wr.u8(rd.u8())
        elif t == 3:                      # number (lua_Number = double, 8B)
            wr.raw(rd.take(8))
        elif t == 4:                      # string
            n = rd.size(size_t)
            if n == 0:
                wr.size(0)
            else:
                s = rd.take(n)
                wr.size(len(s))
                wr.raw(s)
        else:
            raise ValueError("bad constant type %d" % t)
    np = rd.i32()
    wr.i32(np)
    for _ in range(np):
        parse_proto(rd, wr, size_t)
    nli = rd.i32()                        # lineinfo
    wr.i32(nli)
    wr.raw(rd.take(nli * 4))
    nlv = rd.i32()                        # locvars
    wr.i32(nlv)
    for _ in range(nlv):
        n = rd.size(size_t)
        if n == 0:
            wr.size(0)
        else:
            s = rd.take(n)
            wr.size(len(s))
            wr.raw(s)
        wr.i32(rd.i32())
        wr.i32(rd.i32())
    nuv = rd.i32()                        # upvalue names
    wr.i32(nuv)
    for _ in range(nuv):
        n = rd.size(size_t)
        if n == 0:
            wr.size(0)
        else:
            s = rd.take(n)
            wr.size(len(s))
            wr.raw(s)


def convert(data):
    h = data[:12]
    if h[:4] != b"\x1bLua":
        raise ValueError("not lua bytecode")
    if h[4] != 0x51 or h[5] != 0:
        raise ValueError("not lua 5.1 format-0 bytecode (ver %r fmt %r)" % (h[4], h[5]))
    if h[8] not in (4, 8):
        raise ValueError("unexpected sizeof(size_t) byte %r" % h[8])
    out = Writer()
    out.raw(h[:8] + b"\x04" + h[9:12])    # sizeof(size_t) -> 4
    rd = Reader(data)
    rd.take(12)
    parse_proto(rd, out, h[8])
    if rd.pos != len(data):
        raise ValueError("trailing %d bytes after parse end" % (len(data) - rd.pos))
    # verify: re-parse the converted output as ILP32 and require exact consumption
    vd = bytes(out.out)
    vrd = Reader(vd)
    vrd.take(12)
    vwr = Writer()
    parse_proto(vrd, vwr, 4)
    if vrd.pos != len(vd):
        raise ValueError("verification: trailing bytes in converted output")
    return vd


def main():
    path = sys.argv[1]
    data = open(path, "rb").read()
    conv = convert(data)
    open(path, "wb").write(conv)
    print("lua_ilp32: %s %d -> %d bytes" % (path, len(data), len(conv)))


if __name__ == "__main__":
    main()
