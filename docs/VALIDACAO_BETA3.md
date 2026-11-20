# Validação da v0.1.0-beta.3

Registro consolidado em 19/11/2026 e atualizado com os playtests adicionais e o CI do Pull Request #2. A versão foi
**publicada em 19/11/2026** como *pre-release*
([página da release](https://github.com/rogrillo/underkeep-ptbr/releases/tag/v0.1.0-beta.3)), com os mesmos pacotes
validados aqui:
- `Underkeep-PTBR-v0.1.0-beta.3-Windows.zip`, SHA-256 `dfe59db9…f2ad`;
- `Underkeep-PTBR-v0.1.0-beta.3-SteamDeck.zip`, SHA-256 `723340ca…65f1`.

Os tipos de evidência:

- **Playtest:** teste manual em hardware real, relatado pelo mantenedor. Não há log automatizado das sessões.
- **Automático local:** testes `pytest` e testes de fumaça na máquina de desenvolvimento (Windows 11), com o jogo
  instalado e só lido, e pastas Documentos sintéticas.
- **CI:** GitHub Actions do Pull Request #2 (seção 3).

A versão visa **somente a build Steam 26770834** (Underkeep 1.0.6). O instalador recusa outras builds.

## 1. Playtests confirmados pelo mantenedor

| Plataforma | Relato | Evidência |
|---|---|---|
| Windows | instalação e jogo funcionando com a tradução no Underkeep 1.0.6 | playtest |
| Steam Deck | instalação e jogo funcionando com a tradução no Underkeep 1.0.6 | playtest |
| Build antiga | "instalação tentada em uma build antiga: bloqueada corretamente" | playtest |

Os playtests usaram os pacotes candidatos da Fase 2A. Os pacotes finais contêm os **mesmos executáveis, catálogos e
código do instalador**, conferidos arquivo a arquivo. Só o `VERSAO.txt` mudou, para registrar estes playtests.

### Playtests adicionais: textos acrescentados ao slot espanhol

| Verificação | Relato | Evidência |
|---|---|---|
| Página 7 do "Como jogar" | texto em português confirmado dentro do jogo | playtest |
| Página 8 do "Como jogar" | texto em português confirmado dentro do jogo | playtest |
| Poção do esquecimento | item encontrado em uma loja, com nome, descrição e efeito em português exibidos corretamente | playtest |

Essas verificações confirmam que as **cinco entradas acrescentadas** ao slot espanhol aparecem em português:
- as duas páginas do "Como jogar";
- nome, descrição e efeito da poção.

O relato não informa em qual plataforma elas foram feitas, nem se foram repetidas nas duas. O **uso** da poção e a
devolução dos pontos de habilidade não foram relatados (seção 5).

## 2. Testes de fumaça (automático local, pacotes finais)

| Pacote | Resultado |
|---|---|
| `Underkeep-PTBR-v0.1.0-beta.3-Windows.zip` | **18/18** verificações (`scripts/smoke_test_release.py`): executável sem Python no PATH, detecção, bloqueios (versão incompatível, pasta inexistente, sem Documentos, `mods/base` desconhecido), instalação, aviso de outro mod, duplicata recusada, status, desinstalação adulterada recusada, desinstalação, jogo preservado |
| `Underkeep-PTBR-v0.1.0-beta.3-SteamDeck.zip` | **14/14** verificações (`scripts/smoke_test_steamdeck.py`); pack instalado **idêntico hash a hash** ao do instalador Windows |

## 3. Testes automatizados

| Execução | Resultado |
|---|---|
| Suíte `pytest` local (Windows 11, Python 3.13), após a consolidação do repositório | **219 aprovados, 3 pulados, 0 falhas.** Os pulados exigem links simbólicos ou `unzip` do Linux |
| Atualização a partir da Beta 2 (`tests/test_update_from_beta2.py`, jogo e Documentos sintéticos) | aprovado: o pack antigo é detectado como desatualizado; o instalador antigo recusa a build nova; o novo remove a Beta 2 e instala; tudo é bloqueado com o jogo aberto; mods de terceiros são preservados |
| Acréscimo de textos ausentes no slot espanhol (`tests/test_slot_additions.py`) | aprovado |
| Validador do catálogo (`l10n-validate`) | OK: 5.796 entradas; só os 5 avisos `SLOT_ADDITION` esperados |
| Leitura e regravação dos arquivos do jogo 1.0.6 | 107/107 `.rfile` e 22/22 `.db` idênticos byte a byte |
| CI (GitHub Actions), [execução 44650215914](https://github.com/rogrillo/underkeep-ptbr/actions/runs/44650215914), commit `6a5f935` (PR #2) | **aprovado** nos três jobs: `linux` 221 aprovados e 1 pulado; `tests (3.11)` e `tests (3.13)` no Windows, 220 aprovados e 2 pulados cada |

O resultado do CI vale para o commit `6a5f93534fdfc8659d2b5da945ce28d26d52b0e2`. Qualquer commit novo, inclusive só
de documentação, precisa de uma nova execução aprovada antes do merge.

## 4. Revisão editorial pendente

- A tradução cobre **5.796 de 5.796** textos traduzíveis. A revisão humana completa continua em andamento.
- As **30 entradas** criadas, alteradas ou movidas para a versão 1.0.6 estão traduzidas, mas **não passaram por revisão
  humana**:
  - 10 novas: duas páginas do "Como jogar", Poção do esquecimento e nomes do mapa da cidade;
  - 18 retraduzidas: atributos, classes, criação do herói, críticos e Manto das sombras;
  - 2 movidas: Cajado do trovão.
- Problemas de tradução serão corrigidos aos poucos, conforme os playtests e o retorno da comunidade.

## 5. Não comprovado explicitamente pelo playtest

Os relatos do mantenedor confirmam instalação e jogo nas duas plataformas e a exibição dos cinco textos acrescentados
(seção 1). Eles **não detalham** estes pontos, que continuam sem comprovação no jogo:

- Em qual plataforma foram vistos as páginas 7 e 8 e os textos da poção, e se isso foi repetido na outra.
- O **uso** da Poção do esquecimento: devolução dos pontos de habilidade e demais efeitos.
- Os rótulos do mapa da cidade e o tooltip de Constituição, que ficou sem título como no original em inglês.
- Se os textos que cresceram cabem na tela: criação do herói, descrições de classe e tooltips de atributo.
- **Desinstalação no Underkeep 1.0.6.** Foi comprovada no playtest da beta.2 e nos testes automáticos; o código não
  mudou.
- **Atualização com a Beta 2 realmente instalada** em uma pasta Documentos real. Foi coberta só pelos testes
  automáticos e por uma simulação com os executáveis reais e uma pasta sintética.
- No Steam Deck: qual interface foi usada (janela kdialog ou terminal).
- Todos os caminhos narrativos e finais.
- Distribuições Linux além do SteamOS e o Windows 10.
