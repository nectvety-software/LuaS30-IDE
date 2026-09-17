"""Bind a VXP to a Nokia 225 SIM IMSI using cert-id 1. Pure stdlib."""
from __future__ import annotations
import hashlib, struct
from pathlib import Path
TRAILER_SIZE=86; MARKER=b"\xB4VDE10"

def _digits(s):
    s="".join(c for c in str(s) if c.isdigit())
    if not (10<=len(s)<=18): raise ValueError("IMSI must be 10..18 digits")
    return s

def bind(source: Path,target: Path,imsi: str,app_id=None,ram_kb=None,prefix9=True):
    data=Path(source).read_bytes()
    if len(data)<TRAILER_SIZE or data[-TRAILER_SIZE:-80]!=MARKER: raise ValueError("invalid VXP")
    trailer_start=len(data)-TRAILER_SIZE; tags_pos=struct.unpack_from("<I",data,len(data)-12)[0]
    pos=tags_pos; out=bytearray(); imsi_raw=(("9" if prefix9 else "")+_digits(imsi)).encode("ascii")
    while pos+8<=trailer_start:
        tag,n=struct.unpack_from("<II",data,pos);pos+=8;v=data[pos:pos+n];pos+=n
        if tag==0x02 and app_id is not None:v=struct.pack("<I",int(app_id))
        elif tag==0x03:v=struct.pack("<I",1)
        elif tag==0x0F and ram_kb is not None:v=struct.pack("<I",int(ram_kb))
        elif tag==0x12:v=imsi_raw
        out+=struct.pack("<II",tag,len(v))+v
        if tag==0:break
    if pos!=trailer_start: raise ValueError("bad tag stream")
    trailer=MARKER+struct.pack("<I",1)+b"\0"*64+struct.pack("<I",tags_pos)+b"\0"*8
    final=data[:tags_pos]+out+trailer;Path(target).write_bytes(final)
    h=hashlib.sha256(final).hexdigest().upper();Path(str(target)+".sha256").write_text(f"{h} *{Path(target).name}\n",encoding="ascii")
    return h
