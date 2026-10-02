from __future__ import annotations
import subprocess, sys, tempfile
from pathlib import Path

SIG=b"\x1bLua"

class Conv:
    def __init__(self,data:bytes,in_sz:int,out_sz:int):
        self.d=data; self.p=12; self.out=bytearray(data[:12])
        self.in_sz=in_sz; self.out_sz=out_sz
        self.out[8]=out_sz

    def take(self,n:int)->bytes:
        if n<0 or self.p+n>len(self.d):
            raise ValueError(f"truncated chunk at {self.p}, need {n}")
        b=self.d[self.p:self.p+n]; self.p+=n; return b

    def put(self,b:bytes): self.out.extend(b)

    def u8(self)->int:
        b=self.take(1); self.put(b); return b[0]

    def int4(self)->int:
        b=self.take(4); self.put(b); return int.from_bytes(b,"little",signed=True)

    def raw(self,n:int): self.put(self.take(n))

    def string(self):
        b=self.take(self.in_sz)
        n=int.from_bytes(b,"little",signed=False)
        if n>0xffffffff:
            raise ValueError(f"string too large: {n}")
        self.put(int(n).to_bytes(self.out_sz,"little",signed=False))
        if n: self.raw(n)

    def function(self):
        self.string()
        self.int4(); self.int4()
        self.raw(4)  # nups, numparams, is_vararg, maxstacksize

        n=self.int4()
        if n<0: raise ValueError("negative code count")
        self.raw(n*4)

        n=self.int4()
        if n<0: raise ValueError("negative constant count")
        for _ in range(n):
            t=self.u8()
            if t==0:       # nil
                pass
            elif t==1:     # boolean
                self.raw(1)
            elif t==3:     # number
                self.raw(8)
            elif t==4:     # string
                self.string()
            else:
                raise ValueError(f"unsupported constant tag {t} at {self.p-1}")

        n=self.int4()
        if n<0: raise ValueError("negative proto count")
        for _ in range(n):
            self.function()

        n=self.int4()
        if n<0: raise ValueError("negative lineinfo count")
        self.raw(n*4)

        n=self.int4()
        if n<0: raise ValueError("negative locvar count")
        for _ in range(n):
            self.string(); self.int4(); self.int4()

        n=self.int4()
        if n<0: raise ValueError("negative upvalue count")
        for _ in range(n):
            self.string()

    def finish(self)->bytes:
        self.function()
        if self.p!=len(self.d):
            raise ValueError(f"trailing bytes: parsed {self.p} of {len(self.d)}")
        return bytes(self.out)

def convert(data:bytes,in_sz:int,out_sz:int)->bytes:
    if len(data)<12 or data[:4]!=SIG:
        raise ValueError("not a Lua binary chunk")
    if data[4]!=0x51 or data[5]!=0:
        raise ValueError("requires Lua 5.1 format 0")
    if data[6]!=1 or data[7]!=4 or data[9]!=4 or data[10]!=8 or data[11]!=0:
        raise ValueError("unexpected endian/int/instruction/number layout")
    if data[8]!=in_sz:
        raise ValueError(f"expected size_t={in_sz}, got {data[8]}")
    return Conv(data,in_sz,out_sz).finish()

def main(argv:list[str])->int:
    out=None; src=None; strip=False
    i=0
    while i<len(argv):
        a=argv[i]
        if a=="-s":
            strip=True; i+=1
        elif a=="-o" and i+1<len(argv):
            out=Path(argv[i+1]); i+=2
        elif a.startswith("-"):
            raise SystemExit(f"unsupported option: {a}")
        else:
            if src is not None:
                raise SystemExit("exactly one Lua source is supported")
            src=Path(a); i+=1
    if out is None or src is None:
        raise SystemExit("usage: luac_arm32.py [-s] -o OUTPUT INPUT.lua")

    root=Path(__file__).resolve().parent.parent
    host=root/"build"/"_lua51"/"luac.exe"
    if not host.is_file():
        raise SystemExit(f"host Lua 5.1 luac not found: {host}")

    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="luac_arm32_") as td:
        host_chunk=Path(td)/"host.lub"
        cmd=[str(host)]
        if strip: cmd.append("-s")
        cmd += ["-o",str(host_chunk),str(src)]
        cp=subprocess.run(cmd,capture_output=True,text=True)
        if cp.returncode:
            sys.stderr.write(cp.stdout or "")
            sys.stderr.write(cp.stderr or "")
            return cp.returncode
        original=host_chunk.read_bytes()
        arm=convert(original,8,4)
        # Structural round-trip: every field and byte must survive 8->4->8.
        back=convert(arm,4,8)
        if back!=original:
            raise SystemExit("ARM32 chunk conversion round-trip mismatch")
        out.write_bytes(arm)

    b=out.read_bytes()
    if b[:4]!=SIG or b[4]!=0x51 or b[8]!=4:
        raise SystemExit("ARM32 bytecode header verification failed")
    return 0

if __name__=="__main__":
    raise SystemExit(main(sys.argv[1:]))
