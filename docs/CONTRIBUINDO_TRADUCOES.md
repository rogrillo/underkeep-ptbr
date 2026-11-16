# Guia para tradutores e revisores — Underkeep PT-BR

Este guia explica como o catálogo de tradução está organizado e como alterá-lo com segurança.
Regras gerais de contribuição: [CONTRIBUTING.md](../CONTRIBUTING.md).

## 1. Organização do catálogo `l10n/pt-BR/`

| Arquivo | Conteúdo |
|---|---|
| `project.json` | Alvo técnico: pack `base`, slot `es` substituído, idioma de referência `en`, hashes da build suportada |
| `common.json` | Interface (menus, opções, mensagens) |
| `game.json` | Diálogos, narração, missões, placas, nomes de inimigos e locais |
| `items.json` | Nomes e descrições de itens |
| `skills.json` | Nomes e descrições de habilidades |

Cada catálogo é um JSON determinístico (chaves ordenadas, UTF-8, LF), com uma entrada por ID do jogo:

```json
"wizard_first_contact_end_03": {
  "source_sha256": "…64 caracteres…",
  "text": "Começou. Hora de acertar as contas.",
  "translation_status": "translated",
  "review_status": "pending",
  "origin": "ia:lote-14",
  "context": "Opcional: quem fala, situação, decisões de tradução.",
  "review_note": "Opcional: como/por quem foi revisado.",
  "exceptions": [{"code": "LENGTH_OVER_SLOT", "justification": "Motivo com pelo menos 10 caracteres."}]
}
```

- **O texto original não é guardado.** `source_sha256` é o hash do texto inglês de referência. Se o jogo mudar esse
  texto, o validador acusa `STALE_SOURCE`.
- Não altere IDs nem `source_sha256` à mão. Não adicione campos novos, porque o carregador recusa campos desconhecidos.
- `text` é o texto exibido no jogo: preserve as tags e quebras do original (seção 4).

## 2. Estados de tradução e revisão

São dois eixos independentes:

| Campo | Valores | Significado |
|---|---|---|
| `translation_status` | `pending` → `translated` / `needs_review` | se há texto e se ele está válido para a referência atual |
| `review_status` | `pending` → `reviewed` → `approved` / `needs_review` | quanto a tradução foi revisada por pessoas |

- **translated / pending:** texto pronto, ainda sem revisão humana individual. É o estado atual da maior parte do
  catálogo.
- **reviewed:** revisada por uma pessoa (leitura no contexto, glossário conferido).
- **approved:** aprovada por um mantenedor, de preferência após vista no jogo.
- **needs_review:** o original mudou ou há dúvida aberta; não é aplicada no jogo.

Os packs podem ser gerados com as políticas `approved`, `reviewed` ou `translated`. A beta usa `translated`.
Promoções são feitas por mantenedores com `l10n-promote`, sempre com nota rastreável em `review_note`. Ao
corrigir uma entrada, mantenha `translation_status: translated`, volte `review_status` para `pending` se ela
já estava revisada e explique a mudança em `review_note`.

## 3. Glossário e guia de localização

- [GUIA_DE_LOCALIZACAO.md](GUIA_DE_LOCALIZACAO.md) traz as regras de estilo:
  - narração em "você" e NPCs falando com o grupo por "vocês";
  - não presumir o gênero do protagonista;
  - capitalização, pontuação e tratamento de referências e trocadilhos.
- [GLOSSARIO.md](GLOSSARIO.md) traz os termos consolidados. Exemplos: Fonte, Forja das Almas, Fende-almas, portão
  sob a Torre, Senhor da Torre.
- Nomes de itens e habilidades citados em diálogos devem bater com `items.json` e `skills.json`.
- Antes de mudar um termo do glossário, abra uma issue: a mudança precisa ser aplicada em todas as ocorrências.

## 4. Placeholders, tags e quebras (obrigatório)

| Elemento | Exemplo | Regra |
|---|---|---|
| Tags de cor/estilo | `{color_price}`, `{color_ancient_voice}`, `{color:c8c1b3}` | mesmas tags, mesma ordem; o texto entre elas é traduzido |
| Variáveis | `{name}`, `{item_name}`, `%1`, `%2` | nunca traduzir, remover ou duplicar |
| Quebra literal | `\n` (barra + n dentro do texto) | manter a mesma quantidade |
| Quebra real | CRLF em poemas, enigmas e placas | manter a mesma estrutura de linhas |
| IDs `_no_localize` | créditos, nomes técnicos | não traduzir |

Enigmas e pistas precisam continuar solucionáveis em português. A resposta tem prioridade sobre a rima ou o
trocadilho.

## 5. Testes e validador

Testes automatizados (não precisam do jogo):

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Validação do catálogo (precisa do jogo instalado, que é lido em modo somente leitura):

```powershell
.\.venv\Scripts\python.exe scripts\ukloc_cli.py l10n-validate
```

O resultado esperado é `Validação: OK`, sem erros. Principais códigos:

| Código | Tipo | Significado |
|---|---|---|
| `MARKUP_MISMATCH`, `PLACEHOLDER_MISMATCH`, `MARKUP_MALFORMED` | erro | tags ou variáveis diferentes da referência |
| `UNSUPPORTED_GLYPH` | erro | caractere que as fontes do jogo não desenham |
| `STALE_SOURCE` | erro | o texto original mudou desde a tradução |
| `LENGTH_OVER_SLOT` | aviso | texto mais longo que o espaço provável (>115% do maior entre `es` e `en`) |
| `UNTRANSLATED` | aviso | texto idêntico ao original |
| `LINEBREAK_MISMATCH`, `MARKUP_ORDER` | aviso | quebras ou ordem das tags diferentes |

Prefira **corrigir** o texto. Quando o aviso for intencional (nome próprio igual ao original, nome de item que não pode
ser encurtado), registre uma exceção na própria entrada com `code` e `justification` claros. Não enfraqueça as
validações globais.

Quem não tem o jogo instalado pode contribuir por issue ou abrir o PR mesmo assim: um mantenedor roda o validador.

## 6. Contexto e justificativas

- Use `context` para registrar quem fala, a situação e decisões não óbvias, por exemplo: "trocadilho adaptado",
  "feminino porque se refere à Coisa", "pista do enigma preservada".
- Use `review_note` para registrar revisões e correções, por exemplo: "humano:revisão no jogo (cap. 3)" ou
  "corrigido: concordância".
- No PR, explique o **motivo** de cada mudança e cite o glossário ou o guia quando aplicável.
- Não reescreva entradas em massa sem discussão prévia. Uma tradução aprovada (`approved`) só muda com justificativa.
