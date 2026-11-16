<!--
Texto da GitHub Release v0.1.0-beta.2, publicada em 16/11/2026 como pre-release.
Título: Underkeep PT-BR v0.1.0-beta.2 — Primeira Beta Pública. Tag: v0.1.0-beta.2 (commit 2bfa216).
Assets: os dois ZIPs e os dois .sha256 (hashes abaixo). Este comentário não faz parte do texto publicado.
-->

# Underkeep PT-BR v0.1.0-beta.2

**Tradução comunitária, gratuita e não oficial do [Underkeep](https://store.steampowered.com/app/2411200/) para o
português brasileiro**, para Windows e Steam Deck.

> Projeto de fãs, sem afiliação nem endosso da **Rake in Grass**, criadora do jogo. É preciso ter o Underkeep
> **comprado na Steam**. Nenhum arquivo do jogo é distribuído: a tradução é gerada no seu computador, a partir da sua
> própria instalação.

## O que vem nesta versão

- **5.786 de 5.786 textos traduzidos (100%):**
  - diálogos e narrativa, incluindo todos os finais e epílogos: 3.531;
  - interface: 1.102;
  - itens: 838;
  - habilidades: 315.
- Enigmas adaptados com as respostas preservadas, e nomes de itens e habilidades consistentes no jogo todo.
- Instalador para **Windows** (sem precisar de Python) e instalador com janela para **Steam Deck**.
- Desinstalação segura, que devolve o espanhol original.

**Versão beta:** a tradução está completa, mas a revisão humana integral ainda está em andamento. Podem aparecer erros,
frases pouco naturais ou textos longos demais para a tela. Seus relatos ajudam muito.

## Compatibilidade

| | |
|---|---|
| Jogo | Underkeep na Steam, **build 26592006**. Outras builds são recusadas, sem alterar nada |
| Windows 11 (64 bits) | testado: instalação, jogo e desinstalação |
| Steam Deck (SteamOS, modo Desktop, Proton) | testado: janela de instalação, jogo e desinstalação |
| Windows 10, outras distribuições Linux | não testados |

## Downloads

| Arquivo | Para | SHA-256 |
|---|---|---|
| `Underkeep-PTBR-v0.1.0-beta.2-Windows.zip` (16,3 MB) | Windows | `cbfbd5e10f486efb008d80b2e02afbb0a522a23df8d9a8cab932195d7581bb6f` |
| `Underkeep-PTBR-v0.1.0-beta.2-SteamDeck.zip` (0,5 MB) | Steam Deck | `8fd79de5ac9e74d82cb12e9a383cf6ececdcecf625bcf070d6589d06e9f2a912` |

Confira o download:
- **Windows (PowerShell):** `Get-FileHash .\Underkeep-PTBR-v0.1.0-beta.2-Windows.zip -Algorithm SHA256`
- **Steam Deck (Konsole):** `sha256sum -c Underkeep-PTBR-v0.1.0-beta.2-SteamDeck.zip.sha256`

## Instalação no Windows

1. Abra o Underkeep pela Steam uma vez e feche o jogo.
2. Extraia o ZIP inteiro.
3. Execute `Instalar-Underkeep-PTBR.exe`, confirme a pasta do jogo e responda `s`.
4. No jogo: **Opções → Idioma → Español**. Esse idioma passa a mostrar o português.

O executável não tem assinatura digital, então o SmartScreen pode avisar. Só clique em "Executar assim mesmo" se baixou
desta página e conferiu o SHA-256. [Guia completo](https://github.com/rogrillo/underkeep-ptbr/blob/main/docs/INSTALACAO.md)

## Instalação no Steam Deck

1. No modo Jogo, abra o Underkeep uma vez e feche-o.
2. No **modo Desktop**, extraia o ZIP inteiro (Dolphin: botão direito → Extrair → Extrair aqui).
3. Dê dois cliques em `Instalador-Underkeep-PTBR.sh` e escolha **Executar**.
4. Escolha **Instalar a tradução** e confirme.
5. No jogo: **Opções → Idioma → Español**.

Não precisa de `sudo`, senha nem instalar programas. [Guia completo](https://github.com/rogrillo/underkeep-ptbr/blob/main/docs/STEAM_DECK.md)

## Desinstalação

Feche o jogo e:
- **Windows:** execute `Desinstalar-Underkeep-PTBR.exe`;
- **Steam Deck:** abra o `Instalador-Underkeep-PTBR.sh` e escolha **Desinstalar a tradução**.

O espanhol original volta.

## Segurança

O instalador:
- grava **somente** em `Documentos/Underkeep/mods/base`, no Steam Deck dentro do prefixo Proton do jogo;
- **não altera** a pasta da Steam, o executável, os saves, a Steam Cloud nem as configurações;
- confere a build e os hashes do jogo antes de qualquer alteração;
- recusa o jogo aberto, versões diferentes e pastas de outros mods.

Baixe apenas desta página.

## Limitações conhecidas

- A tradução ocupa o lugar do **espanhol**, que fica indisponível enquanto ela estiver instalada.
- **Quando a Steam atualizar o Underkeep, desinstale a tradução** e aguarde uma versão compatível.
- São necessários cerca de 800 MB livres durante a instalação. Ao final, ficam cerca de 370 MB.
- Créditos e nomes de idiomas permanecem no original.
- Revisão humana em andamento.

## Encontrou um problema?

Abra uma [issue](https://github.com/rogrillo/underkeep-ptbr/issues/new/choose) com o modelo **Problema de tradução** ou **Bug técnico**. Informe a versão
(0.1.0-beta.2), a plataforma e onde o texto aparece. Não envie saves, arquivos do jogo nem dados pessoais.

## Créditos e licenças

- **Underkeep** © Rake in Grass. Obrigado pelo jogo! Apoie os desenvolvedores comprando-o e recomendando-o.
- **Tradução e ferramentas:** comunidade Underkeep PT-BR. O primeiro rascunho das traduções e parte das ferramentas
  foram produzidos com auxílio de IA (Claude, da Anthropic), sob supervisão humana. Glossário, decisões editoriais,
  revisão e playtests foram feitos por pessoas.
- **Licenças:** código em MIT; traduções e documentação em CC BY-NC-SA 4.0. Elas valem só para o que o projeto criou e
  não concedem direitos sobre o jogo. Veja o [aviso legal](https://github.com/rogrillo/underkeep-ptbr/blob/main/AVISO_LEGAL.md).

Projeto gratuito e não oficial, feito por fãs para fãs.
