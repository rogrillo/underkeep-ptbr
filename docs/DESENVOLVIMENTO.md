# Guia de desenvolvimento — Underkeep PT-BR

Documento técnico para quem mantém as ferramentas, gera packs ou prepara releases. Público de outros guias:
- **Jogadores:** [README](../README.md) e [guia de instalação](INSTALACAO.md).
- **Tradutores:** [guia de contribuição](CONTRIBUINDO_TRADUCOES.md).

## Princípios

- Fidelidade primeiro: sentido, terminologia, tom e contexto, não apenas tradução literal.
- O jogo é lido **somente em modo leitura**. Nada é gravado na pasta da Steam.
- Ferramentas próprias em **Python 3.11+**, com testes automatizados (`pytest`).
- Catálogo intermediário com IDs estáveis, hashes do texto de referência, contexto e estados de revisão.
- **Nunca publicar assets, executáveis, saves, dumps ou texto extraído do jogo.**

## Estrutura do repositório

```text
ukloc/                  Biblioteca Python: formatos do jogo, catálogo, pack-sombra, instalador, janela do Steam Deck
scripts/                CLI de localização, geração e testes dos pacotes, auditoria de publicação
tests/                  Testes pytest (fixtures sintéticas; nenhum arquivo do jogo)
l10n/pt-BR/             Catálogo da tradução (IDs, hashes, texto PT-BR, estados de revisão)
data/                   Patch de exemplo e exceções justificadas do validador
release/                Pontos de entrada e LEIA-ME dos pacotes Windows e Steam Deck
docs/                   Guias de jogadores e contribuidores, glossário, decisões
assets/screenshots/     Capturas de tela do README (únicas imagens aceitas pela auditoria de publicação)
work/, audit/local/     Saídas locais com material do jogo (ignoradas pelo Git; nunca commitar)
build/, dist/           Artefatos de build e pacotes (ignorados pelo Git)
```

## Ambiente (PowerShell)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

O projeto não precisa estar na pasta do jogo. No Linux, use `python3 -m venv .venv` e `.venv/bin/python`.

## Como o jogo guarda os textos

- Engine própria da Rake in Grass (C++, SDL3, FMOD, Steamworks).
- Textos em `base/text_text_{common,game,items,skills}_{cs,de,en,es,fr,pl,ru}.txt.rfile`, em UTF-8, dentro do
  container `DfT`. O formato é lido e regravado com round-trip byte a byte verificado.
- As fontes do jogo já têm todas as letras do português.
- A lista de idiomas é fixa no executável. Por isso a tradução ocupa o slot `es`.
- Antes do pack `base` da Steam, o jogo procura `Documentos/Underkeep/mods/base/base/`. É aí que o instalador coloca
  o **pack-sombra**: uma cópia local de `base/` em que só as tabelas de texto `es` são substituídas. Nada é gravado
  na pasta da Steam.
- Chave ausente → fallback para inglês → ID cru. A escolha de idioma fica na cvar `language`, em `game_config.txt`.

## Ferramentas de localização (`scripts/ukloc_cli.py`)

O jogo é lido apenas em modo leitura. As saídas ficam em `work/` e `audit/local/`, ignorados pelo Git, porque podem
conter texto ou arquivos do jogo.

```powershell
$G = "C:\Program Files (x86)\Steam\steamapps\common\Underkeep"
.\.venv\Scripts\python.exe scripts\ukloc_cli.py --game-root $G roundtrip       # formatos: regravação idêntica
.\.venv\Scripts\python.exe scripts\ukloc_cli.py --game-root $G gate-unchanged  # catálogo sem alterações -> bytes idênticos
.\.venv\Scripts\python.exe scripts\ukloc_cli.py --game-root $G extract         # tabelas -> work/extract/ (texto original: não commitar)
.\.venv\Scripts\python.exe scripts\ukloc_cli.py --game-root $G pseudo          # pseudo-localização no slot es -> work/pseudo/
.\.venv\Scripts\python.exe scripts\ukloc_cli.py --game-root $G inspect-db      # índices _*.db
```

Os `.rfile` gerados em `work/` **não devem ser copiados para o jogo nem commitados**.

### Pack-sombra

O pack-sombra é montado a partir de um patch JSON (`data/patches/`), que contém só hashes e o texto novo:

```powershell
.\.venv\Scripts\python.exe scripts\ukloc_cli.py shadow-build      # gera em work/shadow/ (lê o jogo, não grava nele)
.\.venv\Scripts\python.exe scripts\ukloc_cli.py shadow-verify     # integridade + compatibilidade com a build instalada
.\.venv\Scripts\python.exe scripts\ukloc_cli.py shadow-install    # DRY-RUN (padrão): mostra o plano e os bloqueios
.\.venv\Scripts\python.exe scripts\ukloc_cli.py shadow-uninstall  # DRY-RUN (padrão)
.\.venv\Scripts\python.exe scripts\ukloc_cli.py shadow-status
```

`--execute` instala ou desinstala de fato em `Documentos\Underkeep\mods\base`. O pack-sombra contém arquivos do jogo:
nunca distribua nem commite.

### Catálogo PT-BR

As traduções ficam em `l10n/pt-BR/<categoria>.json`. Cada entrada tem:
- um ID;
- o hash do texto inglês (o texto original não é guardado);
- o texto PT-BR;
- `translation_status` e `review_status`;
- contexto, terminologia e exceções justificadas.

`l10n/pt-BR/project.json` fixa o alvo (pack `base`, slot `es`) e os hashes da build. As regras editoriais estão em
`docs/GUIA_DE_LOCALIZACAO.md` e os termos em `docs/GLOSSARIO.md`.

```powershell
.\.venv\Scripts\python.exe scripts\ukloc_cli.py l10n-add --category common <id> [<id> ...]  # só acrescenta pending
.\.venv\Scripts\python.exe scripts\ukloc_cli.py l10n-validate                               # tokens, glifos, comprimento, desatualização
.\.venv\Scripts\python.exe scripts\ukloc_cli.py l10n-sheet                                  # planilha com texto original -> work/l10n/
.\.venv\Scripts\python.exe scripts\ukloc_cli.py l10n-build                                  # só entradas approved -> work/shadow/
.\.venv\Scripts\python.exe scripts\ukloc_cli.py l10n-build --policy translated             # experimental, explícito
```

O pack gerado é verificado e instalado com os comandos `shadow-*` acima (`--shadow work\shadow\<nome>`).

**IDs que faltam no slot `es`.** Uma atualização pode trazer textos novos só no inglês. O jogo resolve os textos por
chave e, quando a chave falta no idioma ativo, mostra o inglês. Para traduzir uma entrada dessas, registre nela a exceção
`MISSING_IN_SLOT`, com justificativa. Assim:
- o validador troca o erro pelo aviso `SLOT_ADDITION`;
- o pack-sombra acrescenta o ID ao **fim** da tabela `es`;
- os IDs originais mantêm ordem e valores;
- o ID precisa existir na referência `en` e não pode existir em outra categoria do `es`, porque o jogo funde as tabelas
  e rejeita IDs repetidos.

Sem a exceção, a entrada continua bloqueada.

### Quando o jogo for atualizado

1. Confira a build em `steamapps/appmanifest_2411200.acf` e o SHA-256 do `underkeep.exe`.
2. Rode `roundtrip` e `gate-unchanged`. Se algum formato mudar, pare e investigue antes de qualquer outra etapa.
3. Extraia a build nova em uma pasta própria e compare com a extração da build anterior. O relatório traz só IDs,
   contagens e hashes e fica em `audit/local/`:

   ```powershell
   .\.venv\Scripts\python.exe scripts\ukloc_cli.py extract --out work\<build> --analysis audit\local\<build>.json
   .\.venv\Scripts\python.exe scripts\compare_builds.py --old work\<anterior> --new work\<build> --report audit\local\comparacao.json
   ```

4. Traduza as entradas novas e revise as alteradas. Atualize `source_sha256` só depois de revisar o texto.
5. Atualize `project.json` com os hashes dos arquivos instalados, nunca apenas o número da build.
6. Rode `l10n-validate`, a suíte e os testes de fumaça dos dois pacotes.

## Instalador do jogador e release

O instalador (`ukloc/installer.py` + `ukloc/steam.py`) reaproveita o pipeline acima:

1. Localiza o jogo pela Steam (Registro e `libraryfolders.vdf`, somente leitura).
2. Confere executável, build e hashes contra `l10n/pt-BR/project.json`.
3. Gera o pack-sombra num diretório temporário a partir dos arquivos do próprio jogador.
4. Instala com `shadow.install` (staging, verificação de hashes, renomeação atômica).

A desinstalação usa o manifesto e recusa pastas alteradas ou desconhecidas.

```powershell
.\.venv\Scripts\python.exe -m ukloc.installer --verificar            # a partir do código-fonte (dry-run)
.\.venv\Scripts\python.exe -m ukloc.installer --documentos <pasta>   # Documentos alternativa (testes)
```

No Linux/Steam Deck, o mesmo instalador:
- resolve a pasta Documentos do **prefixo Proton** (`steam.find_proton_documents`) depois de escolher o jogo, e só a
  escolhe sozinho quando ela está na mesma biblioteca do jogo;
- detecta o jogo aberto por `/proc` (`shadow.linux_game_running`);
- tem uma interface gráfica (`ukloc/gui.py`, kdialog/zenity) que só adapta o `Console` do instalador
  (`confirm`/`choose_path`/`progress`), reaproveitando `dispatch`, `run_install`, `run_uninstall` e `run_status`.

Detalhes em [STEAM_DECK.md](STEAM_DECK.md).

Gerar as releases candidatas (não publica nada):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt   # PyInstaller fixado
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\ukloc_cli.py l10n-validate
.\.venv\Scripts\python.exe scripts\build_release.py                   # Windows + Steam Deck (--plataforma windows|steamdeck|todas)
.\.venv\Scripts\python.exe scripts\smoke_test_release.py dist\Underkeep-PTBR-v<versão>-Windows.zip
.\.venv\Scripts\python.exe scripts\smoke_test_steamdeck.py dist\Underkeep-PTBR-v<versão>-SteamDeck.zip [--comparar <mods/base instalado pelo .exe>]
```

| Pacote | Conteúdo |
|---|---|
| `…-Windows.zip` | dois `.exe` (PyInstaller), `dados/pt-BR`, LEIA-ME, VERSAO, `licencas/` (MIT, CC BY-NC-SA 4.0, aviso legal, Python e PyInstaller) |
| `…-SteamDeck.zip` | `Instalador-Underkeep-PTBR.sh` (755), `app/underkeep_ptbr.py` + só os módulos de `ukloc` importados pelo instalador (calculados por `module_files`), `dados/pt-BR`, LEIA-ME, VERSAO e `licencas/` (MIT, CC BY-NC-SA 4.0, aviso legal), tudo em LF |

Os dois ZIPs são determinísticos: data fixa, entradas ordenadas, caminhos POSIX e `create_system=3` com permissões
Unix. Nunca use `Compress-Archive`, que grava `\` nos nomes e quebra a importação no Linux.

`build_release.py` audita cada ZIP:
- extensões e nomes proibidos, incluindo `.pyc`;
- caminhos com `\`, absolutos ou com `..`;
- `__pycache__`;
- permissões e CRLF em `.sh`/`.py`;
- campos do catálogo;
- arquivos fora da lista prevista;
- caminhos e e-mail do desenvolvedor, inclusive dentro do arquivo do PyInstaller;
- presença das licenças e do aviso legal;
- versão do nome do pacote igual à de `VERSAO.txt`, `LEIA-ME.txt` e, no Deck, de `installer.VERSION`.

Os testes de fumaça rodam fora do workspace, contra a instalação real (somente leitura) e pastas Documentos sintéticas:
- `smoke_test_release.py` executa os `.exe` sem Python no PATH;
- `smoke_test_steamdeck.py` executa o pacote extraído com `python -I -B`, como faz o launcher.

Ao final, os dois conferem os hashes do jogo. Ao commitar o launcher, marque-o como executável no Git:
`git add --chmod=+x release/steamdeck/Instalador-Underkeep-PTBR.sh`. O build já grava `755` no ZIP de qualquer forma.

Ao mudar a versão, atualize `VERSION` em `ukloc/installer.py`, `RELEASE_NOTES.md` e `CHANGELOG.md`.

### Auditoria antes de publicar

`scripts/audit_publication.py` varre **todo o histórico Git** (todas as refs, reflog e, com `--objetos-soltos`,
objetos inalcançáveis) e, com `--arvore`, os arquivos ainda não commitados. Ele procura:
- arquivos do jogo, binários e blobs grandes;
- credenciais;
- e-mails e caminhos pessoais, inclusive o nome de usuário e o da máquina;
- e-mails de autor e committer;
- com `--jogo`, trechos idênticos ao texto original do jogo, comparados localmente, sem imprimir o texto.

```powershell
.\.venv\Scripts\python.exe scripts\audit_publication.py --jogo "<pasta do Underkeep>" --objetos-soltos --arvore
```

Saída 1 significa que há bloqueadores. O teste `test_project_history_has_no_blockers` roda a mesma auditoria, sem o
jogo, a cada execução da suíte.

### Publicar uma versão

1. Atualize `VERSION`, `RELEASE_NOTES.md` e `CHANGELOG.md`.
2. Rode a suíte, o `l10n-validate`, o `build_release.py`, os dois testes de fumaça e a auditoria de publicação.
3. Faça o push e confira o CI (jobs `tests (3.11)`, `tests (3.13)` e `linux`).
4. Crie a release como *pre-release* enquanto a versão for beta, anexando os dois ZIPs e os dois `.sha256`.
5. Baixe os arquivos da página da release e confira com `sha256sum -c`.

O hash do ZIP Windows muda a cada build (PyInstaller). O do Steam Deck é reproduzível para a mesma árvore e o mesmo
fim de linha no checkout: os catálogos são copiados byte a byte.

Quando o jogo for atualizado:
1. Rode `extract`.
2. Compare os `STALE_SOURCE` no `l10n-validate`.
3. Revise as entradas afetadas.
4. Atualize os hashes de `project.json`. É uma decisão manual, nunca automática.
