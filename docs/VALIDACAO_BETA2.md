# Validação final da v0.1.0-beta.2

Registro consolidado em 15/11/2026, para a primeira publicação. Separa três tipos de evidência:

- **Playtest:** teste manual em hardware real, relatado pelo mantenedor (com capturas das janelas no caso do Steam
  Deck). Não há log automatizado dessas sessões.
- **CI:** execuções do GitHub Actions deste repositório (aba Actions) e, antes da publicação, do repositório de
  desenvolvimento, que é privado.
- **Automático local:** testes e testes de fumaça rodados na máquina de desenvolvimento (Windows 11).

Compatibilidade comprovada **somente com a build Steam 26592006** do Underkeep. Não há garantia para builds futuras
nem para distribuições Linux além do SteamOS testado.

## 1. Windows 11 — ciclo completo validado

| Etapa | Resultado | Evidência |
|---|---|---|
| Instalação pelo executável independente (sem Python) | aprovada | playtest |
| Detecção automática da instalação Steam | aprovada | playtest |
| Verificação de compatibilidade (executável, build, hashes) | aprovada | playtest |
| Tradução carregada pela engine e jogada | aprovada | playtest |
| Desinstalação e retorno ao espanhol original | aprovada | playtest |
| `.exe` da beta.2 fora do workspace, sem Python no PATH | 18/18 verificações | automático local (`smoke_test_release.py`) |

O relato do mantenedor cobre o instalador Windows. O registro detalhado do playtest é da beta.1. Entre a beta.1 e a
beta.2, o fluxo Windows só mudou no número de versão: as mudanças da beta.2 são na descoberta do prefixo Proton, na
detecção do jogo aberto no Linux e na janela do Steam Deck. O `.exe` da beta.2 passou no teste de fumaça completo.

## 2. Steam Deck / SteamOS — ciclo completo validado com interface gráfica

| Etapa | Resultado | Evidência |
|---|---|---|
| Extração do pacote `…-SteamDeck.zip` e abertura da janela pelo `Instalador-Underkeep-PTBR.sh` | funcionando | playtest |
| Ferramenta de diálogo | `kdialog` do modo Desktop (KDE), com acentuação correta e mensagens compreensíveis | playtest (capturas) |
| Menu com as quatro operações | funcionando | playtest |
| Detecção automática do jogo e do prefixo Proton | confirmada | playtest |
| Verificar (sem alterações) | aprovado | playtest |
| Consultar o status | aprovado | playtest |
| Instalar a tradução | concluído | playtest |
| Tradução carregada no jogo pelo Proton | correta; playtest aprovado | playtest |
| Bloqueio de operação com o jogo aberto | aprovado | playtest, conforme retorno do mantenedor |
| Desinstalar pela interface gráfica | aprovado | playtest |
| Jogo após a remoção da tradução | funcionando normalmente | playtest |
| `sudo` ou instalação manual de Python | **não foram necessários** | playtest |
| beta.1 pelo terminal (Python 3.14.6 do SteamOS) | instalação, jogo e desinstalação aprovados | playtest anterior |

Caminhos observados no aparelho: `/home/deck/.local/share/Steam/steamapps/common/Underkeep` e
`…/steamapps/compatdata/2411200/pfx/drive_c/users/steamuser/Documents`.

**Não informado no retorno do playtest da beta.2:** versões do SteamOS, do Proton e do Python, tempo de instalação e
local dos saves no Deck. Esses itens não são necessários para a publicação, mas ajudam em relatos futuros.

## 3. Testes automatizados

| Execução | Resultado |
|---|---|
| GitHub Actions deste repositório, workflow "Python tests", execução 43788732436, commit inicial `c094d98` (16/11/2026) | **sucesso** nos três jobs: `tests (3.11)` e `tests (3.13)` no Windows, 168 aprovados e 2 pulados cada; `linux` (Ubuntu, Python 3.13), 169 aprovados e 1 pulado (o pulado exige a instalação real do jogo, ausente no CI) |
| Repositório de desenvolvimento (privado), antes da publicação | **sucesso** nos três jobs, inclusive na suíte maior, com testes de ferramentas internas não publicadas |
| Suíte local (Windows 11, com o jogo instalado, só leitura) | 167 aprovados e 3 pulados (links simbólicos e `unzip` exigem Linux); validador do catálogo OK; testes de fumaça: Windows 18/18 e Steam Deck 14/14, com packs idênticos hash a hash entre as plataformas |

O job `linux` cobre o que o Windows não consegue: links simbólicos, `/proc` sintético, extração do ZIP com `unzip`
(permissão do launcher) e o launcher `.sh` no bash nativo. A interface gráfica real não roda no CI: ela foi validada
no playtest.

## 4. O que fica fora desta validação

- Revisão editorial integral da campanha: em andamento. A cobertura é de 100% dos textos traduzíveis.
- Windows 10, outras distribuições Linux, Flatpak da Steam, `zenity` em outros ambientes gráficos.
- Builds do jogo diferentes da 26592006: o instalador recusa.
