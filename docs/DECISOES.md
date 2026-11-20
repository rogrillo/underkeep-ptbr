# Registro de decisões (ADR leve)

## ADR-000 — Fase investigativa
- Data: 2026-11-13
- Decisão: começar com auditoria somente leitura; não escolher formato/engine sem observação.
- Motivo: reduzir riscos técnicos e evitar corromper uma instalação recém-lançada.
- Status: aprovado como diretriz inicial do projeto.

## ADR-001 — Ferramentas
- Data: 2026-11-13
- Decisão: Claude Code + REA para análise; Python 3.11+ em scripts próprios; GitHub inicialmente privado.
- Status: diretriz inicial.

## ADR-002 — Acréscimo de IDs ausentes no slot `es`
- Data: 2026-11-19 (Fase 2A, Underkeep 1.0.6)
- Contexto: a build 26770834 trouxe 5 textos só no `en`, sem equivalente no `es`: `how_to_play_page_7` e `_8`
  (`common`) e `item_respec_potion`, `_desc` e `_feat` (`items`). O pack-sombra só substituía IDs já existentes no slot.
  Sem mudança, esses textos apareceriam em inglês, pelo fallback de chave observado na Fase 1B.
- Decisão: aceitar acréscimos ao fim da tabela do slot, só para entradas do catálogo com a exceção `MISSING_IN_SLOT`
  justificada. As travas são estas:
  - o ID precisa existir na referência `en` e não existir no slot nem em outra categoria do slot;
  - os IDs originais mantêm ordem e valor;
  - o resultado passa por round-trip;
  - o manifesto registra `add: true`.
- Evidência: o jogo já tolera conjuntos de chaves diferentes entre idiomas, por exemplo 98 IDs só no `es` em `game` e
  22 só no `en` em `common` (Fase 1B).
- Playtest: o mantenedor confirmou no jogo as páginas 7 e 8 do "Como jogar" e os textos da Poção do esquecimento
  (nome, descrição e efeito) em português, vistos numa loja. Ver `docs/VALIDACAO_BETA3.md`.
- Status: implementado na branch `update/underkeep-1.0.6` e confirmado em playtest.
