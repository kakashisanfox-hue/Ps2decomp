# Análise do executável PAL SLES_522.02

Análise de cabeçalhos feita localmente com `file`, `readelf` e `sha256sum` em arquivo fornecido pelo usuário. O executável não é armazenado no repositório.

- SHA-256: `48ad558915641430a611238ffbb09b1139958a28c4b78804f3e80828fd001fe9`
- Formato: ELF32, little-endian, MIPS III, executável estático, stripped
- Entrada: `0x0010A008`
- Program headers: 1
- LOAD: offset `0x001000`, virtual `0x0010A000`, filesz `0x1bdef0`, memsz `0x7a8740`, flags RWE, alinhamento `0x1000`
- Seções: 32; incluem `.text`, `.vutext`, `.data`, `.vudata`, `.rodata`, `.gcc_except_table`, `.sdata`, `.sbss`, `.bss`

## Próximos experimentos
1. Inspecionar tabela de seções e instruções MIPS para detectar instruções não suportadas.
2. Avaliar suporte real do PS2Recomp ao código VU e bibliotecas do jogo.
3. Criar um relatório de compatibilidade reproduzível no GitHub Actions.
4. Somente após validação, experimentar recompilação para ARM64.

A ISO e os dados proprietários não devem ser commitados.
