# Validação da v0.1.0-beta.3 (candidata)

Registro consolidado em 19/11/2026. A versão **ainda não foi publicada**. Os tipos de evidência:

- **Playtest:** teste manual em hardware real, relatado pelo mantenedor. Não há log automatizado das sessões.
- **Automático local:** testes `pytest` e testes de fumaça na máquina de desenvolvimento (Windows 11), com o jogo
  instalado e só lido, e pastas Documentos sintéticas.
- **CI:** GitHub Actions. Só roda depois do envio das mudanças ao GitHub; ainda não executado para esta versão.

A versão visa **somente a build Steam 26770834** (Underkeep 1.0.6). O instalador recusa outras builds.

## 1. Playtests confirmados pelo mantenedor

| Plataforma | Relato | Evidência |
|---|---|---|
| Windows | instalação e jogo funcionando com a tradução no Underkeep 1.0.6 | playtest |
| Steam Deck | instalação e jogo funcionando com a tradução no Underkeep 1.0.6 | playtest |
| Build antiga | "instalação tentada em uma build antiga: bloqueada corretamente" | playtest |

Os playtests usaram os pacotes candidatos da Fase 2A. Os pacotes finais contêm os **mesmos executáveis, catálogos e
código do instalador**, conferidos arquivo a arquivo. Só o `VERSAO.txt` mudou, para registrar estes playtests.

## 2. Testes de fumaça (automático local, pacotes finais)

| Pacote | Resultado |
|---|---|
| `Underkeep-PTBR-v0.1.0-beta.3-Windows.zip` | **18/18** verificações (`scripts/smoke_test_release.py`): executável sem Python no PATH, detecção, bloqueios (versão incompatível, pasta inexistente, sem Documentos, `mods/base` desconhecido), instalação, aviso de outro mod, duplicata recusada, status, desinstalação adulterada recusada, desinstalação, jogo preservado |
| `Underkeep-PTBR-v0.1.0-beta.3-SteamDeck.zip` | **14/14** verificações (`scripts/smoke_test_steamdeck.py`); pack instalado **idêntico hash a hash** ao do instalador Windows |

## 3. Testes automatizados

| Execução | Resultado |
|---|---|
| Suíte `pytest` deste repositório (Windows 11, Python 3.13) | **189 aprovados, 3 pulados, 0 falhas.** Os pulados exigem links simbólicos ou `unzip` do Linux |
| Atualização a partir da Beta 2 (`tests/test_update_from_beta2.py`, jogo e Documentos sintéticos) | aprovado: o pack antigo é detectado como desatualizado; o instalador antigo recusa a build nova; o novo remove a Beta 2 e instala; tudo é bloqueado com o jogo aberto; mods de terceiros são preservados |
| Acréscimo de textos ausentes no slot espanhol (`tests/test_slot_additions.py`) | aprovado |
| Validador do catálogo (`l10n-validate`) | OK: 5.796 entradas; só os 5 avisos `SLOT_ADDITION` esperados |
| Leitura e regravação dos arquivos do jogo 1.0.6 | 107/107 `.rfile` e 22/22 `.db` idênticos byte a byte |
| CI (GitHub Actions) | **ainda não executado** para esta versão |

## 4. Revisão editorial pendente

- A tradução cobre **5.796 de 5.796** textos traduzíveis. A revisão humana completa continua em andamento.
- As **30 entradas** criadas, alteradas ou movidas para a versão 1.0.6 estão traduzidas, mas **não passaram por revisão
  humana**:
  - 10 novas: duas páginas do "Como jogar", Poção do esquecimento e nomes do mapa da cidade;
  - 18 retraduzidas: atributos, classes, criação do herói, críticos e Manto das sombras;
  - 2 movidas: Cajado do trovão.
- Problemas de tradução serão corrigidos aos poucos, conforme os playtests e o retorno da comunidade.

## 5. Não comprovado explicitamente pelo playtest

O relato do mantenedor confirma instalação e jogo nas duas plataformas. Ele **não detalha** estes pontos, que
continuam sem comprovação no jogo:

- Exibição em português dos **5 textos acrescentados** ao slot espanhol: páginas 7 e 8 do "Como jogar" e nome,
  descrição e efeito da Poção do esquecimento. Sem o acréscimo, eles apareceriam em inglês.
- O efeito da Poção do esquecimento, os rótulos do mapa da cidade e o tooltip de Constituição, que ficou sem título
  como no original em inglês.
- Se os textos que cresceram cabem na tela: criação do herói, descrições de classe e tooltips de atributo.
- **Desinstalação no Underkeep 1.0.6.** Foi comprovada no playtest da beta.2 e nos testes automáticos; o código não
  mudou.
- **Atualização com a Beta 2 realmente instalada** em uma pasta Documentos real. Foi coberta só pelos testes
  automáticos e por uma simulação com os executáveis reais e uma pasta sintética.
- No Steam Deck: qual interface foi usada (janela kdialog ou terminal).
- Todos os caminhos narrativos e finais.
- Distribuições Linux além do SteamOS e o Windows 10.
