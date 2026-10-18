# Regras definitivas — Downhill Domination Android

## Objetivo
Port nativo Android ARM64 de Downhill Domination (PS2), por recompilação do executável MIPS, utilizando os recursos originais da ISO do usuário.

## Restrições obrigatórias
- NÃO criar emulador genérico de PlayStation 2.
- NÃO integrar PCSX2/AetherSX2 ou qualquer emulador completo escondido no APK.
- NÃO apresentar um seletor de ISO isolado como port funcional.
- Priorizar ferramentas existentes de recompilação estática e código nativo ARM64.
- Desenvolver apenas camadas de compatibilidade específicas necessárias ao jogo (gráficos, áudio, entrada, sistema de arquivos e serviços do PS2).
- A ISO é fonte dos dados originais, mas não pode ser executada diretamente por ARM64 sem recompilação e adaptações.
- Se a estratégia depender de emulação geral, interromper e informar o usuário antes de mudar de abordagem.
- Não publicar arquivos proprietários do jogo ou BIOS no repositório público.

## Critério de sucesso
Gameplay real de Downhill Domination em Android ARM64 a partir de código recompilado, usando dados da ISO original; não basta abrir um menu ou instalar um APK.

## Alvo inicial
PAL SLES_522.02, VER 1.01.
