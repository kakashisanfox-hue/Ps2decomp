# Downhill Domination — Android Recomp Research

Projeto experimental de investigação de recompilação estática do jogo de PS2 para Android ARM64.

## Situação
- Etapa 0: preparar ferramentas e identificar a versão do executável.
- Ainda não há recompilação funcional nem APK jogável.
- Base de referência: https://github.com/ran-j/PS2Recomp (GPL-3.0).
- Não distribuir ISO, executável, BIOS nem assets proprietários.

## Próximos passos
1. Identificar SYSTEM.CNF e nome do ELF na ISO própria.
2. Investigar a viabilidade do PS2Recomp e suas dependências Android.
3. Compilar ferramentas de análise no GitHub Actions.
4. Produzir um relatório técnico antes de iniciar a integração nativa.
