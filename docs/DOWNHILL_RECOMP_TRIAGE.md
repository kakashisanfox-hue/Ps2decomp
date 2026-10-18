# Downhill PAL — Read-only ELF triage

Local analysis of user-provided SLES_522.02 using GNU readelf; no game binaries committed.

- SHA-256: `48ad558915641430a611238ffbb09b1139958a28c4b78804f3e80828fd001fe9`
- Size: 1,864,236 bytes
- ELF32 little endian; MIPS R5900 / MIPS III flags `0x20924001`
- Entry point: `0x0010a008`
- Stripped executable, no usable function symbol table
- `.text`: address `0x0010a000`, size `0x15fd88`
- `.vutext`: address `0x00269d90`, size `0x00a140` (41,280 bytes)
- `.data`: address `0x00273f00`, size `0x020888`
- `.rodata`: address `0x00294800`, size `0x0307f8`

## Engineering implications
The synthetic MIPS smoke test does not establish compatibility with this stripped commercial ELF. The upstream README recommends Ghidra function-map export for stripped games; its runtime has incomplete GS/VU handling.

## Next milestone
1. Derive a function boundary map using Ghidra or equivalent offline analysis.
2. Run PS2Recomp analyzer/recompiler on this exact ELF **locally or in a private environment**, never in public CI artifacts.
3. Capture generated code diagnostics, unsupported instructions, and unresolved calls.
4. Only then attempt Android ARM64 integration.

A public GitHub Actions runner cannot read files uploaded in this chat. Do not add the game binary or encode it into workflow source.
