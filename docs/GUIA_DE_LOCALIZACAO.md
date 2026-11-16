# Guia de localização PT-BR — Underkeep

Versão 0.1 (Fase 1C-B). As regras marcadas *(provisório)* serão confirmadas na revisão humana e no playtest.
Referência editorial: **inglês**. O espanhol é só o slot técnico de destino e serve de régua de espaço disponível.

## 1. Tom e estilo
- Fantasia sombria com toques de ironia seca (descrições de itens brincam com o jogador). Preservar os dois
  registros: a narração é contida, solene, com frases curtas; as descrições de itens podem ter humor.
- Português brasileiro natural. Evitar construções europeias: "estar a fazer", "ecrã", "utilizador", "aldeia" (no
  sentido de vilarejo), mesóclise, "vós".
- Não traduzir palavra por palavra quando houver construção mais idiomática, por exemplo "Do you really want to…?"
  → "Deseja realmente…?".
- Não acrescentar informação narrativa nem explicar o que o original deixa implícito.

## 2. Tratamento do jogador
- Narração em segunda pessoa (*you*): usar **você** implícito, conjugação na 3ª pessoa ("Você mal tinha conquistado
  glória…"), omitindo o pronome quando natural. *(provisório)*
- Diálogos de interface: tratamento neutro e cortês ("Deseja realmente excluir…?").
- Diálogos de `game` (lote 07): os NPCs falam com o grupo e usam **vocês**; as escolhas do jogador ficam em
  infinitivo ("Perguntar quem ele é.") ou na 1ª pessoa do plural ("Queremos conversar."). A narração mantém
  **você**, mesmo quando a ação é do grupo ("Você põe o bilhete na mesa"). O diário de missões fala com o grupo
  ("Vocês encontraram...", "Voltem a..."). Evitar adjetivos e pronomes oblíquos com gênero para o jogador
  ("pronto", "cansado", "recebê-lo"); preferir "você" como objeto ("observa você").
- Vocativos de gênero dirigidos ao jogador ("lad", "boy") são omitidos ou neutralizados (lote 11). O plural
  genérico para o grupo segue a norma ("Bem-vindos", "inteiros"), mas descrições do grupo na narração preferem
  formas neutras ("Ele examina você: roupas rasgadas, sangue...").
- Falas com marcas de dialeto no original (anões: "ye", "makin'") viram registro informal leve em PT-BR ("tá",
  "pra"), sem sotaque caricato. Cada personagem mantém voz própria (Durok solene, Korr rude, Brenna irônica).
- Referências a outras obras (lápides, quadros, nomes de missão; lote 14): usar o nome oficial em PT-BR quando for
  conhecido e reconhecível ("Mundo Invertido", "cria das trevas", "observador"); senão, manter o termo original
  ("Bhaalspawn", "Dustmen", "Sigil"). Trocadilhos são adaptados por um equivalente em PT-BR ("Descanse em
  pedaços", "Fus-Ro-Dançou") e anotados em `context`. Enigmas preservam a resposta antes da rima.

## 3. Nomes próprios
- **Manter no original** até decisão documentada: Underkeep, nomes de personagens, lugares, reinos, armas lendárias e
  nomes de habilidades.
- Decisões futuras serão caso a caso, considerando se o nome é descritivo (ex.: "Shardpiercer") ou um nome de fato.
  Registrar cada decisão no glossário antes de usar.

## 4. Terminologia de RPG
- Seguir o `docs/GLOSSARIO.md`. Termo novo entra primeiro como *provisório*, com contexto.
- Distinções obrigatórias: **round → rodada** e **turn → turno**; **On/Off → Ligado/Desligado** e
  **Enabled/Disabled → Ativado/Desativado**.
- Nomes de efeitos de status (Burn, Freeze, Stun…) só serão fixados depois de vistos na HUD. Até lá, usar verbo ou
  descrição ("chance de queimar o alvo").

## 5. Capitalização (aprovado nas Fases 1E/1F)
- **Caixa de frase em tudo**: botões, menus, rótulos, títulos de painel, nomes de efeitos, traços e mutações
  ("Novo jogo", "Configurações de vídeo", "Pacto de sangue").
- **Exceções**: nomes próprios (Underkeep, Caerlin, Zerethic, Godzilla, Rake in Grass), siglas (XP, PV, NPCs,
  V-Sync), Fervor como recurso, e Vazio em "Invocador do Vazio" (decisão 1F).
- Em frases, nomes de mecânica/estado mantêm a maiúscula quando o original a usa (ex.: "imune a Atordoamento",
  "aplica Sangramento"); verbos e adjetivos ficam em minúsculas ("queimar", "em chamas").
- **Vírgula decimal** só em texto exibido (tooltips com marcação, ex.: "Dano x 1,75"). Valores e fórmulas
  interpretados pelo jogo não são alterados.

## 6. Pontuação e tipografia
- **Não usar** reticências tipográficas (…), aspas curvas (“ ” ‘ ’), travessão/meia-risca (— –) nem €: não há glifo
  nas fontes do jogo (o validador bloqueia). Usar `...`, `"` e `'` retos e hífen `-`.
- Manter a pontuação estrutural do original: dois-pontos em rótulos ("Volume Geral:"), interrogação/exclamação,
  ponto final em dicas. Não usar ¿ ¡.
- Abreviações: minutos → `min`, horas → `h` ("%1h %2min").

## 7. Gênero e número
- Concordar com o substantivo PT-BR, não com o inglês ("a adaga", "o jogo salvo").
- Variáveis podem trazer palavras de gênero desconhecido (ex.: `{hero_name}`, nomes de itens). Prefira construções
  neutras ("o grupo de {hero_name}" em vez de adjetivos que exijam concordância). Registrar casos difíceis no campo
  `context` para revisão.
- Números vindos de variáveis: "{skill_damage} de dano" funciona para singular e plural; evitar "ponto(s)".

## 8. Variáveis, tags e quebras (regras técnicas obrigatórias)
- `%1`, `%2`… (posicionais): manter todos, sem alterar o número. A ordem pode mudar se a frase exigir, desde que o
  conjunto seja o mesmo.
- `{nome}` (variáveis como `{save_name}`, `{skill_damage}`) e tags de estilo (`{color_fire}`, `{a:right}`,
  `{italic}`, `{color:#feffb8}`): copiar exatamente, sem traduzir nem inserir espaços dentro das chaves. Manter a
  tag na mesma posição lógica (ex.: a cor começa no mesmo trecho).
- `\n` literal: manter a mesma quantidade. Posicionar a quebra para equilibrar as linhas em PT-BR.
- Chaves `*_no_localize`: nunca alterar.
- Exceções a essas regras só com justificativa no campo `exceptions` da entrada (o validador exige).

## 9. Textos de interface e espaço
- Régua prática: o texto visível do slot espanhol atual (o validador avisa quando PT-BR passa de 115% dele). ES já
  costuma ser maior que EN, então caber no ES é um bom indício, mas só o playtest confirma.
- Preferir formas curtas consagradas ("Sair", "Voltar") e evitar siglas obscuras.
- Botões: verbo no infinitivo ("Carregar Jogo", "Excluir").

## 10. Formatação de descrições
- Itens: nome e descrição em caixa de frase (seção 5). Respeitar `\n` que separa a linha de efeito (ex.:
  "Rusty.") do texto de sabor.
- Linhas de atributo de habilidade: "Rótulo{a:right}{valor}". O rótulo deve ser curto, porque o valor fica alinhado
  à direita na mesma linha.

## 11. Fluxo de estados e critérios de revisão
| Campo | Valores | Significado |
|---|---|---|
| `translation_status` | `pending` → `translated` / `needs_review` | `needs_review` = o original mudou ou o tradutor marcou dúvida |
| `review_status` | `pending` → `reviewed` → `approved` / `needs_review` | `approved` = liberado para builds normais |

Builds normais usam só `approved`. Builds experimentais podem usar `--policy translated` explicitamente (fica
registrado no relatório e no manifesto).

Checklist do revisor:
1. Sentido fiel ao inglês, sem omissão ou acréscimo.
2. PT-BR natural e no tom da cena (narração × interface × humor de item).
3. Terminologia conforme o glossário; termos novos registrados.
4. Tokens, variáveis e quebras intactos (`l10n-validate` sem erros).
5. Comprimento compatível com a interface (aviso `LENGTH_OVER_SLOT` analisado; conferir no jogo).
6. Gênero e número corretos, inclusive com variáveis.
7. Ambiguidades anotadas em `context`; só então mudar para `reviewed`/`approved`.
