# Identificação da versão do jogo

Identificação visual fornecida pelo proprietário da cópia em 2026-10-17.

- Título: Downhill Domination
- Região: Europa (PAL)
- Executável aparente: `SLES_522.02` (1,78 MB conforme gerenciador de arquivos)
- Imagem: `Downhill Domination (Europe) (En,Fr,De,Es,It).iso`
- `SYSTEM.CNF` presente (58 bytes)
- `IOPRP270.IMG` presente (243 KB)
- Diretórios visíveis: PTS, R, REP, RST, SHELL, SKAT, SND, VAG.

## Verificações pendentes
1. Ler conteúdo de SYSTEM.CNF para confirmar BOOT2.
2. Identificar formato ELF e cabeçalhos do executável.
3. Calcular hash SHA-256 localmente para versionamento, sem publicar arquivos protegidos.
4. Avaliar compatibilidade da versão PAL com o recompilador escolhido.
5. Confirmar licenças de dependências antes de integrar código.

Não publicar ISO, ELF, BIOS nem assets proprietários no repositório.
