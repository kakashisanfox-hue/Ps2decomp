#!/usr/bin/env python3
"""Experimental R5900 -> portable C++ static translator.

Input: privately owned PS2 ELF. Output: C++ source containing translated
instructions from the original .text section. Compile for Android ARM64
with NDK. Unsupported instructions are explicit stops, never silently NOPs.

This is not a complete PS2 recompiler or a playable game runtime.
Do NOT commit generated output from proprietary games to public repos.
"""
import argparse
import pathlib
import struct

def text_section(blob):
    if len(blob)<52 or blob[:6]!=b'\x7fELF\x01\x01' or struct.unpack_from('<H',blob,18)[0]!=8:
        raise ValueError('Expected little-endian ELF32 MIPS')
    shoff=struct.unpack_from('<I',blob,32)[0]
    stride,count,names=struct.unpack_from('<HHH',blob,46)
    if stride<40 or not count or names>=count or shoff+stride*count>len(blob):
        raise ValueError('Invalid section table')
    sections=[struct.unpack_from('<10I',blob,shoff+i*stride) for i in range(count)]
    st=sections[names]
    if st[4]+st[5]>len(blob):raise ValueError('Invalid names table')
    strings=blob[st[4]:st[4]+st[5]]
    for sh in sections:
        off=sh[0]
        if off>=len(strings):continue
        end=strings.find(b'\0',off)
        if end<0 or strings[off:end]!=b'.text':continue
        base,fo,size=sh[3],sh[4],sh[5]
        if size%4 or fo+size>len(blob):raise ValueError('Invalid .text')
        return base,struct.unpack_from('<%dI'%(size//4),blob,fo)
    raise ValueError('Missing .text')

def translate(w,pc):
    op=w>>26;rs=(w>>21)&31;rt=(w>>16)&31;rd=(w>>11)&31
    sh=(w>>6)&31;fn=w&63;imm=struct.unpack('<h',struct.pack('<H',w&65535))[0]
    nextpc=pc+4
    if w==0:return f's.pc=0x{nextpc:08x}u; return true;'
    if op==0:
        if fn==0:return f's.r[{rd}]=int64_t(int32_t(uint32_t(s.r[{rt}])<<{sh})); s.pc=0x{nextpc:08x}u; return true;' if rd else f's.pc=0x{nextpc:08x}u; return true;'
        if fn==2:return f's.r[{rd}]=int64_t(int32_t(uint32_t(s.r[{rt}])>>{sh})); s.pc=0x{nextpc:08x}u; return true;'
        if fn==3:return f's.r[{rd}]=int64_t(int32_t(int32_t(s.r[{rt}])>>{sh})); s.pc=0x{nextpc:08x}u; return true;'
        if fn in (33,35,36,37,38):
            expr={33:f'uint32_t(s.r[{rs}])+uint32_t(s.r[{rt}])',35:f'uint32_t(s.r[{rs}])-uint32_t(s.r[{rt}])',36:f's.r[{rs}]&s.r[{rt}]',37:f's.r[{rs}]|s.r[{rt}]',38:f's.r[{rs}]^s.r[{rt}]'}[fn]
            value=f'int64_t(int32_t({expr}))' if fn in (33,35) else expr
            return f's.r[{rd}]={value}; s.pc=0x{nextpc:08x}u; return true;'
    if op in (9,12,13,14,15):
        expr={9:f'int64_t(int32_t(uint32_t(s.r[{rs}])+uint32_t({imm})))',12:f's.r[{rs}]&{w&65535}u',13:f's.r[{rs}]|{w&65535}u',14:f's.r[{rs}]^{w&65535}u',15:f'int64_t(int32_t({(w&65535)<<16}u))'}[op]
        return f's.r[{rt}]={expr}; s.pc=0x{nextpc:08x}u; return true;'
    # Branches require precise delay-slot execution; do not miscompile them.
    return None

HEADER='''// Generated from private PS2 ELF. Do not redistribute proprietary output.
#include <cstdint>
struct RecompState { uint64_t r[32]{}; uint32_t pc=0; uint32_t fault_pc=0; uint32_t fault_word=0; };
extern "C" bool downhill_recompiled_step(RecompState& s) {
    s.r[0]=0;
    switch(s.pc) {
'''
FOOTER='''    default: s.fault_pc=s.pc; s.fault_word=0; return false;
    }
}
'''
def generate(blob):
    base,words=text_section(blob)
    lines=[HEADER]
    supported=0
    for i,w in enumerate(words):
        pc=base+4*i
        code=translate(w,pc)
        if code is None:
            lines.append(f'    case 0x{pc:08x}u: s.fault_pc=s.pc; s.fault_word=0x{w:08x}u; return false;\n')
        else:
            supported+=1
            lines.append(f'    case 0x{pc:08x}u: {code}\n')
    lines.append(FOOTER)
    return ''.join(lines),supported,len(words),base

def main():
    p=argparse.ArgumentParser()
    p.add_argument('elf',type=pathlib.Path)
    p.add_argument('--output',type=pathlib.Path,required=True)
    a=p.parse_args()
    result,supported,total,base=generate(a.elf.read_bytes())
    a.output.write_text(result)
    print(f'.text base=0x{base:08X}; translated={supported}/{total}; unsupported={total-supported}')
    print('Output is partial, not playable. Do not commit proprietary generated source.')

if __name__=='__main__':main()
