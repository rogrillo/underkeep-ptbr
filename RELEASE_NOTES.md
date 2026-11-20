# Underkeep PT-BR v0.1.0-beta.3

> **Publicada em 19/11/2026** como *pre-release*:
> [página da release v0.1.0-beta.3](https://github.com/rogrillo/underkeep-ptbr/releases/tag/v0.1.0-beta.3), cujo texto
> está em [release/GITHUB_RELEASE_v0.1.0-beta.3.md](release/GITHUB_RELEASE_v0.1.0-beta.3.md).
> Compatível com o **Underkeep 1.0.6** (Steam build `26770834`).

## Novidades

- **Compatibilidade com o Underkeep 1.0.6**, build `26770834`. O instalador reconhece a build nova e continua recusando
  versões incompatíveis sem alterar nada.
- **5.796 de 5.796** entradas traduzíveis identificadas e traduzidas:
  - diálogos e narrativa: 3.536;
  - interface: 1.104;
  - itens: 843;
  - habilidades: 313.
- **Textos novos da 1.0.6:**
  - Poção do esquecimento;
  - páginas 7 e 8 do "Como jogar" (atributos e equipamentos, mecânicas de combate);
  - nomes no mapa da cidade;
  - Cajado do trovão com nome e descrição.
- **Textos alterados pelo patch** foram retraduzidos: atributos, classes, criação do herói, críticos e a habilidade do
  Ladrão, agora **Manto das sombras**.
- **Atualização a partir da Beta 2:** o instalador encontra a versão anterior e oferece removê-la antes de instalar a
  nova.
- **Pipeline e processo de atualização:**
  - comparação automática entre builds do jogo;
  - novos testes de atualização e de segurança;
  - auditoria de publicação reforçada.

## Resultados dos testes

| Plataforma ou verificação | Resultado |
|---|---|
| Windows | instalação e jogo traduzido no Underkeep 1.0.6 testados pelo mantenedor |
| Steam Deck | instalação e jogo traduzido no Underkeep 1.0.6 testados pelo mantenedor |
| Build antiga | instalação bloqueada corretamente |
| Textos acrescentados ao slot espanhol | páginas 7 e 8 do "Como jogar" e textos da Poção do esquecimento confirmados em português no jogo |
| Testes automatizados | aprovados localmente e no CI (Windows e Linux) |
| Testes de fumaça dos dois pacotes | aprovados localmente (Windows 18/18, Steam Deck 14/14) |

O uso da poção, a desinstalação no 1.0.6 e outros pontos ainda sem comprovação em jogo estão listados em
[docs/VALIDACAO_BETA3.md](docs/VALIDACAO_BETA3.md).

## Compatibilidade

| | |
|---|---|
| Jogo | Underkeep **1.0.6**, Steam build **26770834**. Outras versões são recusadas |
| Windows 11 (64 bits) | testado: instalação e jogo |
| Steam Deck (SteamOS, Proton) | testado: instalação e jogo |
| Windows 10, outras distribuições Linux | não testados |

## Atualizar a partir da Beta 2

1. Feche o jogo.
2. Desinstale a Beta 2, ou deixe o instalador da Beta 3 removê-la quando ele perguntar.
3. Instale a Beta 3 e escolha **Español** nas opções de idioma.

Detalhes em [docs/ATUALIZACAO_1.0.6.md](docs/ATUALIZACAO_1.0.6.md).

## Limitações conhecidas

- **Revisão humana em andamento**, inclusive dos textos novos e alterados da 1.0.6. Correções virão conforme os
  playtests e o retorno da comunidade.
- A tradução ocupa o lugar do **espanhol**.
- As falas novas do corvo da taverna são só áudio em inglês; não há texto para traduzir.
- Projeto comunitário, gratuito e não oficial, feito com assistência de IA e supervisão humana, sem afiliação com a
  Rake in Grass.

---

# Underkeep PT-BR v0.1.0-beta.2

> **Primeira beta pública, publicada em 16/11/2026** como *pre-release*. Mesma tradução da beta.1: 5.786 de 5.786
> textos, com a revisão humana completa ainda em andamento. Muda a distribuição: agora há um pacote próprio para o
> Steam Deck, validado no aparelho. Downloads na página da release `v0.1.0-beta.2`, cujo texto está em
> [release/GITHUB_RELEASE_v0.1.0-beta.2.md](release/GITHUB_RELEASE_v0.1.0-beta.2.md).

> [!IMPORTANT]
> **Compatibilidade:** a Beta 2 funciona só com a build 26592006 (Underkeep 1.0.5). Ela não é compatível com a
> atualização 1.0.6 (build 26770834, 19/11/2026). Veja [docs/ATUALIZACAO_1.0.6.md](docs/ATUALIZACAO_1.0.6.md).

## Novidades

- **Pacote Steam Deck** (`Underkeep-PTBR-v0.1.0-beta.2-SteamDeck.zip`, cerca de 0,5 MB):
  - extraia e dê dois cliques em `Instalador-Underkeep-PTBR.sh` no modo Desktop;
  - uma janela (kdialog ou zenity) oferece **instalar, verificar, ver o estado e desinstalar**;
  - usa o Python que já vem no SteamOS, sem `sudo`, sem instalar programas e sem mexer na partição do sistema;
  - encontra o jogo e o **prefixo Proton** sozinho, inclusive no cartão microSD, e pergunta quando há mais de uma
    opção possível;
  - modo terminal como alternativa: `./Instalador-Underkeep-PTBR.sh --terminal`.
- **Segurança no Linux:**
  - detecta o jogo aberto, também pelo Proton;
  - recusa destinos que sejam links simbólicos;
  - verifica permissão de escrita.
- **Windows:** mesmo instalador da beta.1, agora com o número de versão 0.1.0-beta.2. Uma beta.1 instalada é
  detectada, e o instalador oferece trocá-la.

- **Licenças:** código em MIT e traduções e documentação em CC BY-NC-SA 4.0, incluídas nos dois pacotes em
  `licencas/`, junto com o aviso legal.

## Resultados dos testes

| Plataforma | Resultado |
|---|---|
| Windows 11 | instalação pelo `.exe`, detecção da Steam, verificação, tradução no jogo e desinstalação (volta ao espanhol original): **aprovadas** |
| Steam Deck (beta.2) | janela `kdialog`, detecção automática do jogo e do prefixo Proton, verificar, status, instalar, jogar, bloqueio com o jogo aberto e desinstalar pela janela: **aprovados**, sem `sudo` e sem instalar Python |
| Steam Deck (beta.1) | instalação pelo Python do SteamOS (terminal), tradução pelo Proton, `--status` e desinstalação: **aprovadas** |
| CI (GitHub Actions) | Windows (Python 3.11 e 3.13) e Linux (Python 3.13): **aprovados** neste repositório (aba Actions) |

Detalhes e tipo de evidência de cada item: [docs/VALIDACAO_BETA2.md](docs/VALIDACAO_BETA2.md).

## Compatibilidade

| | |
|---|---|
| Jogo | Underkeep na Steam, **build 26592006**. Outras versões são recusadas |
| Testado | Windows 11 64 bits; Steam Deck (SteamOS, modo Desktop, Proton) |
| Não testado | Windows 10, outras distribuições Linux, outras builds do jogo |

Guias: [docs/INSTALACAO.md](docs/INSTALACAO.md) (Windows) e [docs/STEAM_DECK.md](docs/STEAM_DECK.md).

---

# Underkeep PT-BR v0.1.0-beta.1

> **Release candidata, não publicada.** Substituída pela beta.2, com a mesma tradução. Versão **beta**: toda
> a tradução está pronta, mas a revisão humana completa e o playtest de todos os caminhos ainda estão em andamento.

Primeira versão pública da tradução comunitária e não oficial do **Underkeep** (Rake in Grass) para o português
brasileiro.

## Destaques

- **Tradução integral:** 5.786 de 5.786 textos traduzíveis.
  - Diálogos e narrativa: 3.531, incluindo todos os finais e epílogos.
  - Interface: 1.102.
  - Itens: 838.
  - Habilidades: 315.
- **Instalador para Windows**, sem precisar instalar Python:
  - detecta o jogo na Steam, inclusive em outras bibliotecas, ou aceita a pasta escolhida;
  - confere a versão do jogo e os hashes antes de qualquer alteração;
  - gera a tradução a partir dos arquivos do **seu** jogo, porque o pacote não contém nenhum arquivo do Underkeep;
  - instala só em `Documentos\Underkeep\mods\base`, sem tocar na pasta da Steam, nos saves, na Steam Cloud ou nas
    configurações;
  - recusa operações inseguras: jogo aberto, versão diferente, pasta de outro mod ou falta de espaço;
  - inclui desinstalador seguro, baseado no manifesto da instalação.
- **Enigmas adaptados** com as respostas preservadas, e nomes de itens e habilidades consistentes em todo o jogo.

## Compatibilidade

| | |
|---|---|
| Jogo | Underkeep na Steam, **build 26592006** (atualização de 13/11/2026). Outras versões são recusadas |
| Testado | Windows 11 64 bits |
| Não testado | Steam Deck / SteamOS, Linux. **Sem suporte nesta versão** (situação na época; o Steam Deck foi aprovado depois, pelo terminal) |

## Instalação

1. Abra o Underkeep uma vez pela Steam e feche-o.
2. Extraia `Underkeep-PTBR-v0.1.0-beta.1-Windows.zip`.
3. Execute `Instalar-Underkeep-PTBR.exe` e confirme.
4. No jogo, vá em **Opções → Idioma → Español**.

Para desinstalar, execute `Desinstalar-Underkeep-PTBR.exe`. Confira o download com o arquivo `.sha256`:

```powershell
Get-FileHash .\Underkeep-PTBR-v0.1.0-beta.1-Windows.zip -Algorithm SHA256
```

Guia completo: [docs/INSTALACAO.md](docs/INSTALACAO.md).

## Limitações conhecidas

- A tradução substitui o idioma **Español**, que fica indisponível enquanto ela estiver instalada.
- **Após uma atualização do jogo, desinstale a tradução** e aguarde uma versão compatível.
- Revisão humana em andamento: podem existir erros, frases pouco naturais ou textos longos demais para a tela.
- Executáveis sem assinatura digital: o SmartScreen pode alertar.
- Cerca de 800 MB livres durante a instalação; ficam cerca de 370 MB em Documentos.
- Créditos e nomes de idiomas permanecem no original.

## Agradecimentos e créditos

- **Rake in Grass**, por criar o Underkeep. Apoie os desenvolvedores comprando o jogo.
- **Comunidade Underkeep PT-BR**: tradução, revisão, ferramentas e testes.
- A tradução e as ferramentas foram produzidas com auxílio de IA (Claude, da Anthropic), sob supervisão humana.
  Glossário, decisões editoriais e playtests ficaram a cargo de pessoas.

Projeto independente, sem afiliação ou endosso da Rake in Grass. Encontrou um problema? Abra uma issue
("Problema de tradução" ou "Bug técnico").
