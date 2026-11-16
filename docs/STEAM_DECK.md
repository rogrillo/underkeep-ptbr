# Steam Deck / SteamOS — instalação, funcionamento e playtest

> **Situação (15/11/2026)**
> - **beta.2, pacote `…-SteamDeck.zip` com janela de instalação: aprovada no Steam Deck** (playtest do mantenedor).
>   A janela abriu pelo `kdialog` do modo Desktop, com o menu das quatro operações e acentuação correta. O
>   instalador encontrou o jogo e o prefixo Proton sozinho. Verificação, status, instalação, jogo traduzido,
>   bloqueio com o jogo aberto e desinstalação pela janela foram aprovados, e o jogo voltou ao original. Não foi
>   preciso `sudo` nem instalar Python. Detalhes em [VALIDACAO_BETA2.md](VALIDACAO_BETA2.md).
> - **beta.1, pelo terminal: aprovada no Steam Deck.** A instalação usou o Python 3.14 do SteamOS e
>   `python3 -m ukloc.installer`.
> - Compatibilidade comprovada só com a **build Steam 26592006**. Outras distribuições Linux não foram testadas.

## 1. Para jogadores

### Instalar (modo Desktop)

1. No **modo Jogo**, abra o Underkeep pelo menos uma vez e feche o jogo. Isso cria o prefixo Proton e a pasta de
   configuração do jogo.
2. Mude para o **modo Desktop**: botão Steam → Ligar/Desligar → Mudar para o modo Desktop.
3. Extraia **o ZIP inteiro**. No Dolphin: botão direito no ZIP → Extrair → Extrair aqui.
4. Abra a pasta extraída e dê dois cliques em **`Instalador-Underkeep-PTBR.sh`**.
   - Se o KDE perguntar se deseja **executar** ou **abrir** o arquivo, escolha **Executar**.
   - Se abrir um editor de texto, o arquivo perdeu a permissão de execução. Clique com o botão direito →
     Propriedades → Permissões → marque **É executável** e tente de novo. Outra opção é usar o modo terminal.
5. Escolha **Instalar a tradução**. O instalador:
   - encontra o jogo e o prefixo Proton sozinho, ou pergunta quando houver mais de uma opção;
   - mostra as pastas e pede confirmação;
   - gera a tradução a partir dos arquivos do seu jogo, o que leva alguns minutos.
6. Volte ao modo Jogo, abra o Underkeep e escolha **Opções → Idioma → Español**.

### Desinstalar

Feche o jogo, abra o mesmo `Instalador-Underkeep-PTBR.sh` e escolha **Desinstalar a tradução**.

### Modo terminal (alternativa)

No Dolphin, dentro da pasta extraída, pressione **F4** ou use botão direito → Abrir terminal aqui:

```bash
./Instalador-Underkeep-PTBR.sh --terminal      # instalação interativa (perguntas no terminal)
./Instalador-Underkeep-PTBR.sh --verificar     # só verifica; não altera nada
./Instalador-Underkeep-PTBR.sh --status
./Instalador-Underkeep-PTBR.sh --desinstalar
```

- **Sem permissão de execução:** use `bash Instalador-Underkeep-PTBR.sh …`.
- **Pastas manuais:** use `--jogo "<biblioteca>/steamapps/common/Underkeep"` e
  `--documentos "<biblioteca>/steamapps/compatdata/2411200/pfx/drive_c/users/steamuser/Documents"`.

### O que é e o que não é alterado

| Item | Ação |
|---|---|
| `…/compatdata/2411200/pfx/drive_c/users/steamuser/Documents/Underkeep/mods/base` | **criada** na instalação e **removida** na desinstalação, só se estiver intacta |
| Pasta do jogo (`steamapps/common/Underkeep`) | somente leitura |
| `Documents/Underkeep/game_config.txt` e o restante do prefixo | não alterados |
| Saves e Steam Cloud | não alterados. No Windows observamos os saves em `Steam/userdata/<id>/2411200/remote`, fora do prefixo; no Deck, o local equivalente ainda não foi confirmado |
| Sistema (partição do SteamOS, pacotes, `sudo`) | nada é instalado nem pedido |

Os testes automatizados confirmam que nada fora de `mods/base` é tocado. No aparelho, o jogo continuou funcionando
depois dos playtests da beta.1 e da beta.2, mas os saves não foram comparados arquivo a arquivo. Por isso o roteiro de
teste começa com um backup.

### Problemas comuns

| Mensagem | O que fazer |
|---|---|
| "Python 3.11 ou mais novo não foi encontrado" | atualize o SteamOS; a versão usada no playtest da beta.1 já trazia o Python 3.14 |
| "Arquivos do instalador não encontrados" | extraia o ZIP inteiro e rode o script de dentro da pasta extraída |
| "… Documents/Underkeep não existe: abra o Underkeep uma vez" | abra e feche o jogo no modo Jogo, depois tente de novo |
| "não foi possível escolher com segurança a pasta Documentos do Proton" | só aparece no modo `--sim`; rode sem `--sim` para escolher, ou informe `--documentos` |
| "o Underkeep está aberto" | feche o jogo; se a Steam ainda mostrar "Parar", aguarde alguns segundos |
| "versão do jogo não suportada" | o jogo foi atualizado; aguarde uma versão compatível da tradução |
| "pertence a outro mod" ou "alterada fora do instalador" | o instalador não apaga pastas desconhecidas; remova `mods/base` manualmente só se tiver certeza |

## 2. Como funciona (técnico)

O pacote contém:
- `Instalador-Underkeep-PTBR.sh`;
- `app/`, com `underkeep_ptbr.py` e somente os módulos de `ukloc` que o instalador importa, em código-fonte;
- `dados/pt-BR`, com os 4 catálogos e o `project.json`;
- `LEIA-ME.txt` e `VERSAO.txt`.

Não há binários, arquivos do jogo nem caches Python.

1. **Launcher (`.sh`).** Confere se os arquivos existem e procura `python3`/`python` com versão ≥ 3.11. Depois executa
   `python3 -I -B app/underkeep_ptbr.py`:
   - `-I` isola o Python de `PYTHONPATH`, do site do usuário e do diretório atual;
   - `-B` evita gravar `__pycache__` na pasta extraída.

   O launcher não manipula o pack.
2. **Interface (`ukloc/gui.py`).** Escolhe a ferramenta de diálogo:
   - usa `kdialog`, o do KDE, presente no modo Desktop;
   - se não houver, usa `zenity`;
   - sem tela gráfica ou sem nenhum dos dois, cai no instalador de terminal, abrindo o Konsole se necessário.

   Os diálogos são chamados com `subprocess` e argumentos em lista, sem shell. Instalar, verificar, consultar o status
   e desinstalar usam **exatamente** os fluxos de `ukloc/installer.py` do Windows, com as mesmas verificações.
3. **Descoberta (`ukloc/steam.py`, somente leitura).**
   - **Raízes da Steam:** `~/.local/share/Steam`, `~/.steam/steam`, `~/.steam/root` e Flatpak. Links simbólicos são
     comparados pelo caminho real e não viram instalações duplicadas.
   - **Bibliotecas:** vêm do `libraryfolders.vdf`, incluindo o microSD (`/run/media/…`).
   - **Jogo:** encontrado pelo `appmanifest_2411200.acf`, campo `installdir`.
   - **Prefixo:** `<biblioteca>/steamapps/compatdata/2411200/pfx/drive_c/users/steamuser/Documents`, ou
     `My Documents` em Protons antigos.
4. **Escolha do prefixo:**
   - **Automática** só quando é inequívoca: o prefixo está na **mesma biblioteca** do jogo e há uma única pasta
     Documents ali, ou uma única que já contém `Underkeep`.
   - **Jogador escolhe** nos demais casos: prefixo só em outras bibliotecas, vários candidatos ou jogo fora do layout
     da Steam.
   - **Nenhum prefixo:** o instalador pede a pasta manualmente.
   - **Modo `--sim`:** uma escolha incerta é **recusada**.
5. **Jogo aberto (`ukloc/shadow.py`).** No Linux, procura em `/proc/*/cmdline` um argumento cujo nome de arquivo seja
   `underkeep.exe`, como o processo Wine/Proton e os auxiliares da Steam. O instalador e o processo pai são ignorados.
   Sem acesso a `/proc`, considera o jogo aberto (falha segura).
6. **Segurança, igual ao Windows:**
   - preflight de executável, build e hashes;
   - instalação transacional (staging, verificação e `os.replace`) somente em `mods/base`;
   - recusa pastas de outros mods, instalações alteradas e destinos que sejam **links simbólicos**, que nunca são
     seguidos nem apagados;
   - verifica permissão de escrita e espaço livre;
   - desinstala pelo manifesto.

### Backup

O instalador **não** faz backup, e a decisão foi deliberada:
- ele não escreve em nenhum dado existente do jogador, só cria `mods/base`;
- copiar saves exigiria ler pastas da Steam fora do escopo do instalador;
- um backup automático daria uma falsa garantia.

O roteiro da seção 4 traz um backup manual, claramente identificado, para o playtest.

## 3. Gerar o pacote

```powershell
.\.venv\Scripts\python.exe scripts\build_release.py --plataforma steamdeck                     # só o ZIP do Deck
.\.venv\Scripts\python.exe scripts\smoke_test_steamdeck.py dist\Underkeep-PTBR-v0.1.0-beta.2-SteamDeck.zip
```

O ZIP é gerado com Python (`zipfile`), nunca com `Compress-Archive`:
- caminhos POSIX com `/`;
- `create_system=3`, para o Ark e o `unzip` respeitarem as permissões;
- permissão `755` no `.sh` e `644` no resto;
- LF nos scripts;
- data fixa, o que torna o ZIP determinístico.

A auditoria recusa barras invertidas, `__pycache__`/`.pyc`, CRLF em `.sh`/`.py`, permissões erradas, arquivos do jogo,
dados privados e arquivos fora da lista prevista. O `.gitattributes` mantém `*.sh` com LF no Git.

## 4. Roteiro de playtest manual no Steam Deck

Roteiro usado na validação da beta.2. Serve também para validar versões futuras.

> Faça no **modo Desktop**. Não pule o backup. Se algum resultado divergir do esperado, **pare**, anote e relate.
> Nenhum passo pede `sudo`.

**0. Preparar**
- Copie para o Deck `Underkeep-PTBR-v0.1.0-beta.2-SteamDeck.zip` e o `.zip.sha256`, por exemplo via pendrive ou KDE
  Connect, para `~/Downloads`.
- Confirme que a tradução da beta.1 **não** está instalada. Se estiver, desinstale-a antes. A beta.2 também oferece
  trocar a versão anterior, mas isso é o passo 9.
- Confira o hash no Konsole:
  ```bash
  cd ~/Downloads && sha256sum -c Underkeep-PTBR-v0.1.0-beta.2-SteamDeck.zip.sha256
  ```
  Esperado: `…SteamDeck.zip: OK`.

**1. Backup** (feche o jogo e espere a Steam Cloud sincronizar):
```bash
B=~/underkeep_backup_$(date +%F_%H%M); mkdir -p "$B"
cp -a ~/.local/share/Steam/userdata/*/2411200 "$B/userdata_2411200" 2>/dev/null
cp -a ~/.local/share/Steam/steamapps/compatdata/2411200/pfx/drive_c/users/steamuser/Documents/Underkeep "$B/Documents_Underkeep"
ls -R "$B" | head -30
```
Se o jogo estiver no microSD, troque o caminho do `compatdata` pela biblioteca do cartão. Anote **onde ficaram os
saves**: isso confirma ou corrige a tabela da seção 1.

**2. Extração e permissões.** Extraia pelo Dolphin com Extrair aqui. Depois, no Konsole:
```bash
cd ~/Downloads/Underkeep-PTBR-v0.1.0-beta.2-SteamDeck && ls -l Instalador-Underkeep-PTBR.sh
```
Esperado: `-rwxr-xr-x`, ou seja, executável. Anote se o Ark preservou a permissão.

**3. Abertura por duplo clique.** No Dolphin, dê dois cliques em `Instalador-Underkeep-PTBR.sh`. Anote o que o KDE
mostrou: a pergunta Executar/Abrir, o editor de texto ou a execução direta. Esperado: a janela "Underkeep PT-BR
0.1.0-beta.2" com o menu de 4 opções.

**4. Verificar (não altera nada).** Escolha **Verificar se dá para instalar**.
- **Esperado:** a confirmação da pasta do jogo e, em seguida, uma mensagem com "Jogo compatível (build Steam
  26592006)", "Pasta Documentos do Proton (prefixo do jogo): …/compatdata/2411200/pfx/drive_c/users/steamuser/Documents"
  e "Modo verificação: … Nada foi alterado".
- **Confira** que a pasta `…/Documents/Underkeep/mods` **não** foi criada.

**5. Status.** Escolha **Ver o estado da instalação**. Esperado: "Tradução: não instalada".

**6. Instalar.**
1. Escolha **Instalar a tradução**.
2. Confira as pastas na pergunta "Instalar a tradução agora?" e escolha **Sim**.
3. Deve surgir um aviso de "Gerando os arquivos traduzidos…". Ao final, a mensagem esperada é "Pronto! Tradução
   0.1.0-beta.2 instalada (5786 textos)".
4. Anote quanto tempo levou.

Depois:
```bash
./Instalador-Underkeep-PTBR.sh --status
```
Esperado: "instalada (0.1.0-beta.2)", sem problemas.

**7. Bloqueio com o jogo aberto.**
1. Com o jogo aberto pelo modo Desktop (Steam → Jogar), rode `./Instalador-Underkeep-PTBR.sh --desinstalar`.
2. Esperado: "o jogo está em execução: feche-o antes", sem remover nada.
3. Feche o jogo.

**8. Jogar.**
1. No modo Jogo, abra o Underkeep e escolha **Opções → Idioma → Español**.
2. Confira o menu, uma conversa, um item e uma habilidade.
3. Feche o jogo e confira o log:
   ```bash
   grep -n "resource pack" ~/.local/share/Steam/steamapps/compatdata/2411200/pfx/drive_c/users/steamuser/Documents/Underkeep/game_log.txt
   ```
   Esperado: `Opening resource pack ".../mods/base/base"`.
4. Confira que o save continua carregando e o progresso está intacto.

**9. (Opcional) Atualização.** Se quiser testar a troca de versão, instale a beta.1 pelo terminal antigo e rode a
beta.2. Esperado: a pergunta "Desinstalar a versão anterior e instalar esta?".

**10. Desinstalar pela janela.**
1. Feche o jogo e abra o instalador.
2. Escolha **Desinstalar a tradução** e confirme.
3. Esperado: "Tradução removida…", e `…/Documents/Underkeep/mods` não existe mais.
4. No jogo, o espanhol original deve voltar.

**11. Terminal (fallback).** Rode `./Instalador-Underkeep-PTBR.sh --verificar` e
`./Instalador-Underkeep-PTBR.sh --terminal`, este último respondendo `N` na confirmação. Esperado: as mesmas mensagens,
sem alterações.

**12. Conferência final.** Compare o backup com o estado atual:
```bash
diff -r "$B/Documents_Underkeep" ~/.local/share/Steam/steamapps/compatdata/2411200/pfx/drive_c/users/steamuser/Documents/Underkeep
```
Esperado: diferenças somente em `game_log.txt` e, se o jogo gravou opções, em `game_config.txt`. Os saves devem
continuar íntegros.

**Relatar:**
- versão do SteamOS e do Proton, e `python3 --version`;
- onde ficaram os saves (passo 1);
- a permissão após a extração (passo 2);
- o comportamento do duplo clique (passo 3);
- a ferramenta de diálogo usada, kdialog ou zenity, e se os textos acentuados apareceram corretamente;
- o tempo de instalação;
- prints de cada janela;
- as saídas dos passos 6, 7 e 11;
- a linha do `game_log.txt`;
- qualquer divergência.

**Se algo der errado:**
1. Feche o jogo.
2. Tente `./Instalador-Underkeep-PTBR.sh --desinstalar`.
3. Se ele recusar, apague manualmente só `…/Documents/Underkeep/mods/base`.
4. Restaure o backup do passo 1, se necessário.
5. Verifique a integridade dos arquivos do jogo na Steam.

## 5. O que está comprovado e o que não está

Legenda: **playtest** = relatado pelo mantenedor após teste no aparelho; **CI** = execução registrada no GitHub
Actions; **automático** = testes locais.

| Item | Evidência |
|---|---|
| Instalação, jogo pelo Proton e desinstalação (beta.1, terminal) | **playtest** |
| Extração do ZIP, abertura da janela pelo `.sh` e menu de 4 operações (beta.2) | **playtest**, com capturas das janelas do KDE |
| `kdialog` real, com acentuação correta | **playtest** |
| Detecção automática do jogo e do prefixo Proton | **playtest**; casos de microSD, ambiguidade, ausência, `My Documents` e links simbólicos cobertos por testes automáticos e pelo CI Linux |
| Verificar, status, instalar, desinstalar pela janela | **playtest** |
| Tradução no jogo e jogo original após a desinstalação | **playtest** |
| Bloqueio com o jogo aberto (detecção por `/proc` com o Proton real) | **playtest**, conforme retorno do mantenedor; `/proc` sintético nos testes automáticos |
| Sem `sudo` e sem instalar Python | **playtest** (Python já presente no SteamOS testado) |
| Testes Linux sem interface gráfica (links simbólicos, `/proc`, extração com `unzip`, launcher) | **CI**: job `linux` do workflow "Python tests", execução 43780046137 no commit `4d30ee3`, 173 testes aprovados e 1 pulado (instalação do jogo ausente no CI) |
| Pacote extraído gera o mesmo pack que o instalador Windows | **automático**: teste de fumaça, pack idêntico hash a hash |
| Local dos saves no Deck, tempo de instalação, versões do SteamOS/Proton/Python na beta.2 | **não informados** no retorno do playtest |
| Outras distribuições Linux, outras builds do jogo, instalação via Flatpak | **não testados** |
