#!/usr/bin/env python3
"""Offline, read-only triage for a PS2 ELF. No game bytes are uploaded."""
import argparse, hashlib, json, struct
from pathlib import Path

def report(path):
    data = Path(path).read_bytes()
    if data[:6] != b"\x7fELF\x01\x01":
        raise ValueError("Expected little-endian ELF32")
    e = struct.unpack_from("<HHIIIIIHHHHHH", data, 16)
    machine, shoff, shentsize, shnum, stridx = e[1], e[5], e[10], e[11], e[12]
    if machine != 8 or shentsize < 40 or shoff + shentsize * shnum > len(data):
        raise ValueError("Invalid MIPS section table")
    headers = [struct.unpack_from("<IIIIIIIIII", data, shoff + i * shentsize) for i in range(shnum)]
    nameshdr = headers[stridx]
    names = data[nameshdr[4]:nameshdr[4] + nameshdr[5]]
    sections = {}
    for h in headers:
        end = names.find(b"\0", h[0])
        name = names[h[0]:end].decode("ascii", "replace") if end >= 0 else ""
        sections[name] = {"address": h[3], "offset": h[4], "size": h[5]}
    code = sections[".text"]
    words = struct.unpack_from("<" + "I" * (code["size"] // 4), data, code["offset"])
    jumps = sum((w >> 26) in (2, 3) for w in words)
    branches = sum((w >> 26) in (1, 4, 5, 6, 7, 20, 21, 22, 23) for w in words)
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
            "entry": hex(e[3]), "text_instructions": len(words),
            "direct_jumps_calls": jumps, "conditional_branches": branches,
            "vu_microcode_bytes": sections.get(".vutext", {}).get("size", 0),
            "notes": ["Instruction counts are heuristic, not recovered functions.",
                      "This is not a recompilation or a compatibility test."]}

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("elf")
    a = p.parse_args()
    print(json.dumps(report(a.elf), indent=2))
