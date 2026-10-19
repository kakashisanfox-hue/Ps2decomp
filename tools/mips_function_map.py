#!/usr/bin/env python3
"""Conservative MIPS ELF function-seed and CFG explorer; stdlib only.

No executable instructions or assets are emitted. Reachability is heuristic:
MIPS delay slots, indirect branches, exceptions and function overlaps need review.
"""
import argparse
import collections
import hashlib
import json
import struct
from pathlib import Path

CONDITIONAL = {1, 4, 5, 6, 7, 20, 21, 22, 23}
LIKELY_REGIMM = {2, 3, 18, 19}

def parse_text(blob):
    if len(blob) < 52 or blob[:6] != bytes.fromhex('7f454c460101'):
        raise ValueError('Expected ELF32 little-endian')
    e = struct.unpack_from('<HHIIIIIHHHHHH', blob, 16)
    if e[1] != 8:
        raise ValueError('Expected MIPS ELF')
    entry, shoff, stride, count, strindex = e[3], e[5], e[10], e[11], e[12]
    if stride < 40 or not count or strindex >= count or shoff + count*stride > len(blob):
        raise ValueError('Invalid ELF section headers')
    sections = [struct.unpack_from('<IIIIIIIIII', blob, shoff+i*stride) for i in range(count)]
    strings = sections[strindex]
    if strings[4]+strings[5] > len(blob):
        raise ValueError('Invalid ELF string table')
    table = blob[strings[4]:strings[4]+strings[5]]
    for s in sections:
        end = table.find(b'\0', s[0])
        if end >= 0 and table[s[0]:end] == b'.text':
            base, offset, size = s[3], s[4], s[5]
            if size % 4 or offset + size > len(blob) or not base <= entry < base+size:
                raise ValueError('Invalid .text or entry')
            return entry, base, struct.unpack_from('<'+'I'*(size//4),blob,offset)
    raise ValueError('Missing .text')

def scan(blob, max_functions=10000, max_instructions=2000000):
    entry, base, words = parse_text(blob)
    end = base + len(words)*4
    valid = lambda pc: base <= pc < end and pc % 4 == 0
    calls = collections.Counter()
    indirect_sites = []
    for i, word in enumerate(words):
        pc = base + 4*i
        op = word >> 26
        if op == 3:
            dest = ((pc+4)&0xf0000000)|((word&0x3ffffff)<<2)
            if valid(dest):
                calls[dest] += 1
        elif op == 0 and (word&63) == 9:
            indirect_sites.append(pc)
    seeds = sorted(set(calls)|{entry})
    if len(seeds) > max_functions:
        raise ValueError('Too many function candidates; raise --max-functions')
    seedset = set(seeds)
    functions = []
    all_visited = set()
    truncations = 0
    for start in seeds:
        queue = collections.deque([start])
        visited = set()
        edges = 0
        indirect = 0
        exits = 0
        truncated = False
        while queue:
            pc = queue.popleft()
            if not valid(pc) or pc in visited or (pc != start and pc in seedset):
                continue
            if len(visited) >= max_instructions:
                truncated = True
                break
            visited.add(pc)
            w = words[(pc-base)//4]
            op = w >> 26
            succ = []
            if op in (2, 3):
                dest = ((pc+4)&0xf0000000)|((w&0x3ffffff)<<2)
                if op == 3:
                    succ = [pc+8]
                else:
                    succ = [dest]
            elif op == 0 and (w&63) in (8, 9):
                if (w&63) == 9:
                    indirect += 1
                    succ = [pc+8]
                else:
                    exits += 1
            elif op in CONDITIONAL:
                imm = w&0xffff
                if imm&0x8000:
                    imm -= 0x10000
                dest = (pc+4+(imm<<2))&0xffffffff
                # REGIMM BLTZAL/BGEZAL are conditional calls: fall through.
                if op == 1 and ((w>>16)&31) in (16,17,18,19):
                    succ = [pc+8]
                else:
                    succ = [pc+8,dest]
            else:
                succ = [pc+4]
            # Mark delay-slot instruction, but do not follow its control flow independently.
            if (op in (2,3,4,5,6,7,20,21,22,23) or
                (op == 1) or (op == 0 and (w&63) in (8,9))):
                delay = pc+4
                if valid(delay):
                    visited.add(delay)
            for dest in succ:
                if valid(dest):
                    edges += 1
                    if dest not in visited:
                        queue.append(dest)
        all_visited.update(visited)
        if truncated:
            truncations += 1
        functions.append({
            'start':hex(start), 'direct_callers':calls[start],
            'reachable_instructions_estimate':len(visited),
            'indirect_calls':indirect, 'indirect_or_return_exits':exits,
            'edges_examined':edges, 'truncated':truncated
        })
    return {
        'input_sha256':hashlib.sha256(blob).hexdigest(),
        'entry':hex(entry), 'text_start':hex(base), 'text_end':hex(end),
        'function_seed_count':len(seeds), 'direct_call_sites':sum(calls.values()),
        'indirect_call_sites_linear':len(indirect_sites),
        'unique_instructions_covered_estimate':len(all_visited),
        'text_instructions':len(words), 'truncated_function_count':truncations,
        'functions':functions,
        'limitations':[
            'Function seeds are heuristic and not confirmed function boundaries.',
            'Linear direct-call discovery may include false positives from embedded data.',
            'CFG is conservative and does not resolve indirect jumps, jump tables or exceptions.',
            'Delay-slot instructions are counted but not modeled for branch-likely execution.',
            'This report is not proof of recompilation or game execution.'
        ]
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument('elf',type=Path)
    p.add_argument('--output',type=Path)
    p.add_argument('--max-functions',type=int,default=10000)
    p.add_argument('--max-instructions',type=int,default=2000000)
    a=p.parse_args()
    if a.max_functions < 1 or a.max_instructions < 1:
        p.error('Limits must be positive')
    result=scan(a.elf.read_bytes(),a.max_functions,a.max_instructions)
    report=json.dumps(result,indent=2)+'\n'
    if a.output:
        a.output.write_text(report)
    else:
        print(report,end='')

if __name__=='__main__':
    main()
