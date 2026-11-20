# Fluxo de trabalho e VS Code

Este repositório é a **única fonte** do projeto: código, testes, catálogos, documentação e pacotes de release saem
daqui. Não existe outro repositório envolvido no desenvolvimento nem na publicação.

## Fluxo de uma mudança

1. **Branch nova** a partir do `main` atualizado.
2. **Preparação das alterações**, por pessoas ou pelo assistente de IA (Claude Code), sempre sob supervisão humana.
3. **Testes automatizados e auditoria de publicação** (seção [Antes de cada commit](#antes-de-cada-commit)).
4. **Revisão** do diff pelo mantenedor.
5. **Commits**, feitos pelo mantenedor.
6. **Push** da branch, feito pelo mantenedor.
7. **Pull Request e CI:** os três jobs precisam passar.
8. **Merge** depois da aprovação.
9. **Build final e GitHub Release**, quando houver nova versão.

O assistente de IA nunca faz commit, push, merge, tag nem release.

## O que fica fora do Git

| Onde | O quê |
|---|---|
| `UKLOC_LOCAL_DIR` (pasta fora do repositório) | extrações, packs-sombra e inventários com material do jogo; ver [DESENVOLVIMENTO.md](DESENVOLVIMENTO.md#pasta-local-fora-do-repositório-ukloc_local_dir) |
| `.local/` | anotações, relatórios internos e rascunhos do mantenedor |
| `CLAUDE.md`, `.claude/` | instruções e configurações locais do assistente |
| `.venv/`, `build/`, `dist/`, `work/`, `audit/local/` | ambiente e artefatos locais |
| `.vscode/` | configurações pessoais do editor |

Todos estão no `.gitignore`. A auditoria de publicação **também** bloqueia material interno, arquivos do jogo e
metadados de imagens, mesmo que alguém force a adição. Arquivos do jogo, saves e dados pessoais nunca devem ficar
dentro da pasta do repositório.

## VS Code

### Abrir e preparar o ambiente

1. **Arquivo → Abrir Pasta…** e escolha a pasta do repositório.
2. Instale a extensão **Python**, da Microsoft.
3. Crie o ambiente no terminal integrado (**Terminal → Novo Terminal**, PowerShell):

   ```powershell
   py -3 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
   ```

4. **Ctrl+Shift+P → Python: Select Interpreter** → escolha `.venv`.

Para gerar os pacotes de release, instale também `requirements-build.txt` (PyInstaller).

### Testes (aba Testing)

1. Abra a aba **Testing** (ícone do frasco).
2. Se pedir, clique em **Configure Python Tests** → **pytest** → pasta raiz (`.`).
3. Use **Run All Tests**. Falhas aparecem em vermelho, com a mensagem ao clicar.

No terminal, `.\.venv\Scripts\python.exe -m pytest -q -rf` mostra o mesmo resultado, com as falhas listadas no fim.
Alguns testes usam a instalação real do Underkeep, só para leitura, e são pulados quando ela não existe. Os testes que
dependem do Linux (links simbólicos, `unzip`) são pulados no Windows e rodam no CI.

### Revisar o diff (Source Control)

- A aba **Source Control** (Ctrl+Shift+G) separa **Staged Changes** (já preparado para o commit) e **Changes** (ainda
  não preparado).
- Clique em um arquivo para ver o diff lado a lado.
- Arquivos binários, como as capturas, aparecem só como alterados; abra a imagem para conferir.

### Preparar arquivos ou trechos

- **Arquivo inteiro:** botão **+** ao lado do arquivo.
- **Só um trecho:** no diff, selecione as linhas → botão direito → **Stage Selected Ranges**.
- **Desfazer a preparação:** botão **−** em Staged Changes. Isso não apaga a alteração.

Um commit inclui **apenas** o que está em Staged Changes. O restante continua na árvore de trabalho para o próximo
commit.

### Branches, commit, push e Pull Request

1. **Branch:** clique no nome da branch na barra inferior → **Create new branch…**.
2. **Commit:** escreva a mensagem na caixa do Source Control e clique em **Commit**.
3. **Push:** **Publish Branch** (primeira vez) ou **Sync Changes**.
4. **Pull Request:** pelo link que o GitHub mostra depois do push, ou com a extensão **GitHub Pull Requests**.

Antes do primeiro merge pelo GitHub, ative em **GitHub → Settings → Emails** a opção **Keep my email addresses
private**. Assim o commit de merge usa o endereço `noreply`.

### CI

Na aba **Checks** do Pull Request ou em **Actions**, confira os três jobs obrigatórios:
- `tests (3.11)` e `tests (3.13)`: Windows;
- `linux`: Ubuntu.

O merge só é liberado com os três verdes.

## Antes de cada commit

```powershell
.\.venv\Scripts\python.exe -m pytest -q -rf
.\.venv\Scripts\python.exe scripts\ukloc_cli.py l10n-validate
.\.venv\Scripts\python.exe scripts\audit_publication.py --arvore --objetos-soltos --jogo "<pasta do Underkeep>"
```

Rode cada comando separadamente e só faça o commit se não houver falhas nem bloqueadores. Sem o jogo instalado, omita
`--jogo`: a comparação com o texto original é pulada.

## Preparar os pacotes de release

1. Atualize `VERSION` (`ukloc/installer.py`), `RELEASE_NOTES.md` e `CHANGELOG.md`.
2. Gere os pacotes (eles vão para `dist/`, que é ignorado):

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
   .\.venv\Scripts\python.exe scripts\build_release.py --plataforma todas
   ```

3. Rode os testes de fumaça:
   - `scripts\smoke_test_release.py dist\<pacote Windows>.zip`;
   - `scripts\smoke_test_steamdeck.py dist\<pacote Steam Deck>.zip --comparar <mods\base instalado pelo Windows>`.
4. Faça o playtest e crie a GitHub Release. Detalhes em [DESENVOLVIMENTO.md](DESENVOLVIMENTO.md#publicar-uma-versão).
