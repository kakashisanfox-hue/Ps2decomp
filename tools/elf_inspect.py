#!/usr/bin/env python3
"""Read-only ELF32/MIPS header and section analyzer. Python stdlib only."""
import argparse, hashlib, json, struct
from pathlib import Path

def analyze(path):
    b = Path(path).read_bytes()
    if len(b) < 52 or b[:4] != b"\x7fELF" or b[4] != 1:
        raise ValueError("Expected ELF32 executable")
    endian = "<" if b[5] == 1 else ">" if b[5] == 2 else None
    if not endian:
        raise ValueError("Unsupported byte order")
    fields = struct.unpack_from(endian + "HHIIIIIHHHHHH", b, 16)
    typ, machine, version, entry, phoff, shoff, flags, ehsize, phentsize, phnum, shentsize, shnum, shstrndx = fields
    if machine != 8:
        raise ValueError("Expected MIPS ELF (e_machine=8)")
    if shoff + shnum * shentsize > len(b):
        raise ValueError("Section headers exceed file size")
    sections = []
    raw = [struct.unpack_from(endian + "IIIIIIIIII", b, shoff + i * shentsize) for i in range(shnum)]
    if shstrndx >= len(raw):
        raise ValueError("Invalid section string table")
    st = raw[shstrndx]
    if st[4] + st[5] > len(b):
        raise ValueError("Invalid string table")
    strings = b[st[4]:st[4]+st[5]]
    for sh in raw:
        offset = sh[0]
        end = strings.find(b"\0", offset)
        name = strings[offset:end if end >= 0 else len(strings)].decode("ascii", "replace") if offset < len(strings) else "?"
        sections.append({"name": name, "type": sh[1], "address": hex(sh[3]), "size": sh[5]})
    return {"file": Path(path).name, "sha256": hashlib.sha256(b).hexdigest(),
            "size": len(b), "machine": machine, "entry": hex(entry),
            "flags": hex(flags), "program_headers": phnum, "sections": sections}

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("elf")
    p.add_argument("--output", default="-")
    a = p.parse_args()
    report = json.dumps(analyze(a.elf), indent=2)
    if a.output == "-":
        print(report)
    else:
        Path(a.output).write_text(report + "\n")
