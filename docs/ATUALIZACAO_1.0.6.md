# Underkeep 1.0.6 e a tradução PT-BR

Nota para quem usa a **Underkeep PT-BR v0.1.0-beta.2**.

> **A Beta 3, compatível com o Underkeep 1.0.6, já está disponível:**
> [Underkeep PT-BR v0.1.0-beta.3](https://github.com/rogrillo/underkeep-ptbr/releases/tag/v0.1.0-beta.3).

## O que aconteceu

Em 19/11/2026 o Underkeep recebeu a atualização **1.0.6 (Character Respec)**, build Steam **26770834**. A Beta 2 da
tradução foi preparada para a build anterior, **26592006 (1.0.5)**, e **não é compatível com a 1.0.6**.

## Se você tinha a Beta 2 instalada

A tradução instalada é uma cópia completa dos dados do jogo da versão 1.0.5, guardada em
`Documentos\Underkeep\mods\base`. O jogo carrega essa pasta no lugar dos arquivos originais. Depois da atualização,
ela pode esconder o conteúdo novo da 1.0.6 ou causar falhas. **Esse comportamento não foi testado.**

**Desinstale a Beta 2 antes de jogar a versão 1.0.6:**

1. Feche o Underkeep.
2. Remova a tradução:
   - **Windows:** execute `Desinstalar-Underkeep-PTBR.exe`, da pasta extraída da Beta 2.
   - **Steam Deck:** no modo Desktop, abra `Instalador-Underkeep-PTBR.sh` e escolha **Desinstalar a tradução**.
3. Pronto: o jogo volta a usar só os arquivos originais da Steam, com todos os idiomas oficiais.

O desinstalador da Beta 2 continua funcionando depois da atualização do jogo. Ele confere que a pasta é a que ele
criou e que não foi modificada, e remove só essa pasta. Saves, configurações e outros mods não são tocados.

Para conferir o estado, execute `Instalar-Underkeep-PTBR.exe --status` (Windows) ou escolha **Ver o estado** no
Steam Deck. Se o jogo mudou desde a instalação, aparece o aviso "O jogo mudou desde a instalação".

## Se você ainda não tinha instalado

O instalador da Beta 2 **recusa** a build 26770834 e não altera nada. A mensagem será "versão do jogo não suportada".
Isso é esperado: use a Beta 3.

## Beta 3 para o Underkeep 1.0.6

A **[v0.1.0-beta.3](https://github.com/rogrillo/underkeep-ptbr/releases/tag/v0.1.0-beta.3)** foi publicada em
19/11/2026 para a build 26770834. Instalação e jogo foram testados no Windows e no Steam Deck.

1. Feche o jogo.
2. Baixe o ZIP da sua plataforma na página da release e confira o SHA-256.
3. Execute o instalador da Beta 3:
   - Windows: `Instalar-Underkeep-PTBR.exe`;
   - Steam Deck: `Instalador-Underkeep-PTBR.sh`.

   Se a Beta 2 ainda estiver instalada, o instalador oferece removê-la antes de instalar a nova.
4. No jogo, escolha **Español** nas opções de idioma.

O instalador da Beta 3, como o da Beta 2, recusa builds diferentes da que ele suporta.
