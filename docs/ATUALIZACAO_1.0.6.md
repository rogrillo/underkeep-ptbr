# Underkeep 1.0.6 e a tradução PT-BR

Nota para quem usa a **Underkeep PT-BR v0.1.0-beta.2**.

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
Isso é esperado.

## Próxima versão

Uma versão da tradução para a 1.0.6 está em preparação. Ela só será publicada depois dos testes no Windows e no
Steam Deck. Acompanhe a página de releases do projeto. Até lá, jogue a 1.0.6 em um dos idiomas oficiais.

Quando a nova versão sair, basta executar o instalador dela. Se a Beta 2 ainda estiver instalada, o instalador
oferece removê-la antes de instalar a nova.
