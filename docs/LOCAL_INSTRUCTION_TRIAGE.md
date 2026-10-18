# Downhill SLES_522.02 — local MIPS instruction triage

Source: user's ELF, inspected offline. No proprietary bytes committed.

| Metric | Value |
|---|---:|
| SHA-256 | `48ad558915641430a611238ffbb09b1139958a28c4b78804f3e80828fd001fe9` |
| Entry point | `0x10a008` |
| `.text` size | `0x15fd88` bytes |
| 32-bit words in `.text` | 360,290 |
| Direct J/JAL opcodes (heuristic) | 20,021 |
| Conditional branch opcodes (heuristic) | 26,383 |
| `.vutext` | 41,280 bytes |

The opcode totals are approximate instruction counts, **not** a function map or proof of successful recompilation.

## Next gate
Run the actual PS2Recomp analyzer against the private ELF and inspect its TOML output. Because GitHub Actions cannot access the chat attachment and the repository is public, no game file is uploaded by the workflow. Next engineering task: establish a safe local or private toolchain path for this test, or derive a Ghidra function map.
