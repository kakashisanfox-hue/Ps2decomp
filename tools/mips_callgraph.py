#!/usr/bin/env python3
"""Offline MIPS ELF32 control-flow discovery. No game content is copied to GitHub."""
import argparse
import collections
import json
import struct
from pathlib import Path

BRANCHES = {1, 4, 5, 6, 7, 20, 21, 22, 23}

def inspect(data: bytes, limit=250):
    if len(data) < 52 or data[:6] != b"\x7fELF\x01\x01":
        raise ValueError("Expected little-endian ELF32")
    e = struct.unpack_from("<HHIIIIIHHHHHH", data, 16)
    if e[1] != 8:
        raise ValueError("Expected MIPS machine")
    entry, shoff, entsize, count, names_idx = e[3], e[5], e[10], e[11], e[12]
    if entsize < 40 or not count or names_idx >= count or shoff + count * entsize > len(data):
        raise ValueError("Invalid section headers")
    sections = [struct.unpack_from("<IIIIIIIIII", data, shoff + i * entsize) for i in range(count)]
    st = sections[names_idx]
    if st[4] + st[5] > len(data):
        raise ValueError("Invalid section names")
    names = data[st[4]:st[4] + st[5]]
    code = None
    for s in sections:
        pos = s[0]
        end = names.find(b"\0", pos)
        name = names[pos:end] if 0 <= pos < len(names) and end >= 0 else b""
        if name == b".text":
            code = s
            break
    if code is None or code[4] + code[5] > len(data) or code[5] % 4:
        raise ValueError("Missing or malformed .text")
    base, offset, size = code[3], code[4], code[5]
    if not base <= entry < base + size:
        raise ValueError("Entry outside .text")
    words = struct.unpack_from("<" + "I" * (size // 4), data, offset)
    calls = collections.Counter()
    edges = collections.Counter()
    indirect_calls = []
    returns = []
    branches = 0
    for i, word in enumerate(words):
        pc = base + i * 4
        op = word >> 26
        if op in (2, 3):
            target = ((pc + 4) & 0xf0000000) | ((word & 0x03ffffff) << 2)
            if base <= target < base + size:
                edges[(pc, target)] += 1
                if op == 3:
                    calls[target] += 1
        elif op == 0:
            funct = word & 63
            rs = (word >> 21) & 31
            if funct == 9:
                indirect_calls.append(hex(pc))
            elif funct == 8 and rs == 31:
                returns.append(hex(pc))
        elif op in BRANCHES:
            branches += 1
            displacement = (word & 0xffff)
            if displacement & 0x8000:
                displacement -= 0x10000
            target = (pc + 4 + (displacement << 2)) & 0xffffffff
            if base <= target < base + size:
                edges[(pc, target)] += 1
    ranked = sorted(calls.items(), key=lambda x: (-x[1], x[0]))
    return {
        "entry": hex(entry), "text_start": hex(base), "text_end": hex(base + size),
        "instruction_count": len(words), "direct_call_sites": sum(calls.values()),
        "unique_direct_call_targets": len(calls),
        "conditional_branch_count": branches,
        "indirect_call_sites": len(indirect_calls), "return_instruction_candidates": len(returns),
        "top_call_targets": [{"address": hex(addr), "call_sites": hits} for addr, hits in ranked[:limit]],
        "entry_in_call_targets": entry in calls,
        "notes": [
            "Static instruction decoding only: data words inside .text may produce false positives.",
            "Indirect calls, delay slots, function boundaries and jump tables require further analysis.",
            "Only addresses and counts are exported; no proprietary instructions or game bytes."
        ]
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("elf", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = inspect(args.elf.read_bytes())
    payload = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(payload)
    else:
        print(payload, end="")

if __name__ == "__main__":
    main()
