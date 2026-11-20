# Instalação e desinstalação — Underkeep PT-BR

Guia para jogadores no **Windows 10/11 (64 bits)**. O ciclo completo (instalação, jogo traduzido e desinstalação com
retorno ao espanhol) foi validado no Windows 11; o Windows 10 não foi testado. Para o **Steam Deck**, use o pacote
`…-SteamDeck.zip` e o guia [STEAM_DECK.md](STEAM_DECK.md), também validado no aparelho. Resultados:
[VALIDACAO_BETA2.md](VALIDACAO_BETA2.md).

## Antes de começar

- Tenha o Underkeep instalado pela Steam, na build suportada pela versão da tradução (veja `VERSAO.txt` no ZIP).
- Abra o jogo **uma vez** e feche-o. Isso cria a pasta `Documentos\Underkeep`.
- Deixe ~800 MB livres no disco da pasta Documentos e no disco da pasta temporária do Windows.
- Confira o download: no PowerShell, `Get-FileHash .\Underkeep-PTBR-v0.1.0-beta.2-Windows.zip -Algorithm SHA256` deve
  mostrar o mesmo valor do arquivo `.sha256` publicado junto com a release.

## Instalar

1. Extraia o ZIP inteiro (não execute de dentro do ZIP).
2. Dê dois cliques em `Instalar-Underkeep-PTBR.exe`.
   Se o SmartScreen avisar, clique em **Mais informações → Executar assim mesmo**, mas só depois de conferir o SHA-256.
3. O instalador procura o jogo nas bibliotecas da Steam, inclusive em outros discos. Pressione **Enter** para aceitar
   a pasta encontrada ou cole outro caminho, que pode ser a pasta do jogo ou o próprio `underkeep.exe`.
4. Ele confere o executável, a build e os hashes dos arquivos de texto. Se tudo estiver certo, pergunta se deve
   instalar: responda `s`.
5. A tradução é gerada a partir dos arquivos do seu jogo e instalada em
   `Documentos\Underkeep\mods\base`. Isso leva cerca de um minuto.
6. Abra o jogo, vá em **Opções → Idioma** e escolha **Español**.

### O que o instalador nunca faz

- Gravar na pasta da Steam ou alterar o `underkeep.exe`.
- Mexer em saves, Steam Cloud, `game_config.txt` ou no Registro do Windows (ele só *lê* onde a Steam está instalada).
- Sobrescrever uma pasta `mods\base` criada por outro mod ou manualmente.
- Instalar com o jogo aberto, com uma versão diferente do jogo ou sem espaço em disco.

Se algo falhar no meio da instalação, os arquivos parciais são removidos automaticamente.

## Desinstalar

Feche o jogo e execute `Desinstalar-Underkeep-PTBR.exe`. Ele confere se a pasta `mods\base` é a que o instalador criou
e se não foi modificada, e só então a remove. Outros mods em `Documentos\Underkeep\mods` não são tocados. Depois disso,
o jogo volta a usar apenas os arquivos originais da Steam, com o espanhol original.

## Atualizar a tradução

Execute o instalador da versão nova. Se houver uma versão anterior instalada, ele oferece removê-la e instalar a nova.

## Quando o jogo for atualizado

A tradução instalada contém uma cópia dos dados do jogo da versão para a qual foi gerada. **Após uma atualização do
Underkeep na Steam, desinstale a tradução antes de jogar** e aguarde uma versão compatível. O instalador recusa
versões diferentes do jogo, e o comando `--status` avisa quando o jogo mudou desde a instalação.

**Underkeep 1.0.6 (19/11/2026):** a Beta 2 não é compatível com a versão 1.0.6 do jogo. Se ela estiver instalada,
desinstale-a antes de jogar. Detalhes em [ATUALIZACAO_1.0.6.md](ATUALIZACAO_1.0.6.md).

## Opções avançadas

Execute pelo Prompt de Comando ou PowerShell, dentro da pasta extraída:

| Comando | Efeito |
|---|---|
| `Instalar-Underkeep-PTBR.exe --verificar` | só verifica compatibilidade e destino; não altera nada |
| `Instalar-Underkeep-PTBR.exe --status` | mostra se a tradução está instalada e se o jogo mudou |
| `Instalar-Underkeep-PTBR.exe --jogo "D:\SteamLibrary\steamapps\common\Underkeep"` | usa esta pasta do jogo |
| `Instalar-Underkeep-PTBR.exe --documentos "E:\Docs"` | usa outra pasta Documentos (que contenha `Underkeep`) |
| `Desinstalar-Underkeep-PTBR.exe --verificar` | mostra o que seria removido |

Códigos de saída: `0` sucesso, `2` operação bloqueada com segurança (nada alterado), `1` erro.

## Solução de problemas

| Mensagem | O que fazer |
|---|---|
| "versão do jogo não suportada" / "arquivo(s) de texto do jogo diferente(s)" | O jogo foi atualizado ou modificado. Na Steam, use **Propriedades → Arquivos instalados → Verificar integridade** e aguarde uma versão compatível da tradução |
| "Documentos\Underkeep não existe" | Abra o jogo uma vez pela Steam e feche-o |
| "o Underkeep está aberto" | Feche o jogo (confira na bandeja do sistema) |
| "pertence a outro mod ou foi criado manualmente" | Já existe `Documentos\Underkeep\mods\base` que não é desta tradução. Remova ou mova esse mod manualmente, se quiser usar a tradução |
| "foi alterada fora do instalador" | Alguém modificou os arquivos instalados. Por segurança, o desinstalador não apaga a pasta; feche o jogo e apague `Documentos\Underkeep\mods\base` manualmente |
| O jogo continua em inglês | Escolha **Español** em Opções → Idioma |
| Texto cortado ou estranho | Abra uma issue do tipo "Problema de tradução" |

Ao relatar um problema, copie as mensagens exibidas pelo instalador e informe a versão da tradução e do Windows.
