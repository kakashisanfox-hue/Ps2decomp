# Dia 1 — análise de fluxo de controle do ELF de PS2

Ferramenta: `tools/mips_callgraph.py` (somente Python padrão).

## Uso local, com uma cópia legítima do executável

```bash
python3 tools/mips_callgraph.py /caminho/privado/SLES_522.02 --output downhill-map.json --limit 1000
python3 -m unittest discover -s tests -p test_mips_callgraph.py -v
```

**Não envie o executável, ISO, arquivos de jogo ou o código extraído ao repositório público.**
O JSON contém endereços, contagens e relações estáticas, não bytes do jogo.
Inspecione-o antes de compartilhar.

O relatório inclui SHA-256, endereço de entrada, limites da seção .text,
candidatos de entrada de função, chamadas diretas internas e externas,
chamadas indiretas, possíveis retornos, destinos de saltos e ramificações.

### Limitações importantes

- Os candidatos a função **não** são funções recuperadas e validadas.
- A análise percorre a seção .text linearmente: dados embutidos podem gerar falsos positivos.
- Instruções em delay slots, caminhos dinâmicos, tabelas de salto, chamadas indiretas e
  sobreposições de código/dados ainda exigem análise adicional.
- Nenhum código proprietário é recompilado ou executado por essa ferramenta.
- O CI testa exclusivamente um ELF sintético; **não tem acesso ao SLES_522.02**.

### Próximo bloqueio real

Para recuperar as funções originais e alimentar o PS2Recomp, é necessário executar
a análise sobre o ELF legítimo em ambiente privado e verificar o resultado.
O mapa por si só não garante compilação ou execução do jogo.
