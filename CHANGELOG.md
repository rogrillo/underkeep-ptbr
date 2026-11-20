# Changelog

Histórico de mudanças por versão do Underkeep PT-BR. Notas para jogadores: [RELEASE_NOTES.md](RELEASE_NOTES.md).

## [Não lançado]

### Repositório único

Este repositório passa a ser a única fonte do projeto. Não há mais exportação a partir de outro repositório.

- **[docs/FLUXO_DE_TRABALHO.md](docs/FLUXO_DE_TRABALHO.md):** fluxo de branch, revisão, commits, CI e release, e guia do
  VS Code.
- **`UKLOC_LOCAL_DIR`:** extrações, packs-sombra e inventários podem ficar numa pasta fora do repositório. Uma pasta
  dentro dele é recusada.
- **Auditoria de publicação:**
  - bloqueia material interno em qualquer pasta (`CLAUDE.md`, relatórios `FASE_*.md`, `.local/`, entre outros);
  - bloqueia metadados em capturas de tela: PNG só com `IHDR`/`PLTE`/`IDAT`/`IEND`; JPEG e WebP sem EXIF, XMP, IPTC ou
    comentários.
- **`scripts/audit_inventory.py`:** inventário só com metadados da instalação, usado para comparar builds quando o jogo
  é atualizado.
- **`.gitignore`:** ignora `.local/`, `CLAUDE.md`, `.claude/` e configurações pessoais do VS Code.

### Em preparação: adaptação ao Underkeep 1.0.6 (candidata 0.1.0-beta.3)

Ainda não lançada. A Beta 2 continua sendo a versão publicada e só funciona no Underkeep 1.0.5 (build 26592006).

- **Homologação** ([docs/VALIDACAO_BETA3.md](docs/VALIDACAO_BETA3.md)):
  - o mantenedor confirmou instalação e jogo no Underkeep 1.0.6 no Windows e no Steam Deck, e o bloqueio em uma build
    antiga;
  - testes de fumaça dos pacotes finais aprovados: Windows 18/18 e Steam Deck 14/14;
  - o documento lista o que o playtest não comprovou explicitamente.
- **`VERSAO.txt` dos pacotes** separa o que foi testado no playtest da beta.3 e o que vem de playtests anteriores.
- **Galeria do README:** captura nova do menu principal no Underkeep 1.0.6, sem metadados; as legendas dizem a versão
  de cada imagem.

- **Nota para jogadores da Beta 2** ([docs/ATUALIZACAO_1.0.6.md](docs/ATUALIZACAO_1.0.6.md)): desinstale a Beta 2
  antes de jogar a 1.0.6. O README e as notas da Beta 2 avisam disso.
- **Catálogo** atualizado para a build 26770834:
  - 10 entradas novas: duas páginas do "Como jogar", a Poção do esquecimento e os nomes no mapa da cidade;
  - 18 entradas retraduzidas porque o original mudou: atributos, classes, criação do herói, críticos e
    Manto das sombras;
  - o Cajado do trovão foi movido de `skills` para `items`, como no jogo;
  - total: 5.796 de 5.796 textos traduzíveis. As entradas novas e alteradas aguardam revisão humana.
- **Pack-sombra:** pode acrescentar ao slot `es` textos que o jogo novo só traz em inglês. Isso exige a exceção
  `MISSING_IN_SLOT` justificada na entrada. Os IDs originais não mudam de ordem nem de valor. Detalhes em
  `docs/DECISOES.md` (ADR-002).
- **`scripts/compare_builds.py`:** compara a localização de duas builds e o catálogo. O relatório traz só IDs,
  contagens e hashes.
- **Testes novos:** acréscimos ao slot e atualização a partir de uma Beta anterior (jogo atualizado, instalador antigo
  recusando, instalador novo substituindo, jogo aberto, mods de terceiros).
- Glossário, guia de desenvolvimento (procedimento para atualizações do jogo) e modelos de issue atualizados.

### Documentação e ferramentas publicadas após a Beta 2

- README com uma galeria de 4 capturas de tela do jogo em português (`assets/screenshots/`): menu, missões, ficha do
  personagem e itens.
- Auditoria de publicação:
  - aceita imagens só em `assets/screenshots/`, com até 1 MB cada;
  - passa a enxergar todos os caminhos de arquivos com conteúdo idêntico.
- O teste do pacote Steam Deck extraído é pulado quando o Underkeep está aberto na máquina, porque o instalador
  recusa instalar com o jogo aberto.
  - **Melhoria futura:** tornar esse teste independente da detecção real de processos (por exemplo, simulando a
    detecção), sem mudar o comportamento do instalador.

## [0.1.0-beta.2] — 16/11/2026 — primeira beta pública

- **Pacote Steam Deck** (`Underkeep-PTBR-v0.1.0-beta.2-SteamDeck.zip`):
  - launcher `Instalador-Underkeep-PTBR.sh` que usa o Python do SteamOS, sem `sudo` e sem instalar programas;
  - janela de instalação em `kdialog` (com `zenity` como alternativa), com instalar, verificar, ver o estado e
    desinstalar;
  - detecção automática do jogo e do prefixo Proton, inclusive no microSD, perguntando quando há mais de uma opção;
  - modo terminal como alternativa.
- **Segurança no Linux:**
  - detecta o jogo aberto, inclusive pelo Proton;
  - recusa destinos que sejam links simbólicos;
  - verifica permissão de escrita.
- **Pacotes reproduzíveis:** ZIPs com caminhos POSIX e permissões Unix, e auditoria automática (arquivos do jogo,
  dados pessoais, caches, fins de linha, licenças, versão).
- **Licenças:** MIT para o código; CC BY-NC-SA 4.0 para traduções e documentação, sem nenhum direito sobre o jogo;
  aviso legal nos pacotes.
- **Validação:**
  - Windows 11: ciclo completo;
  - Steam Deck: ciclo completo pela janela `kdialog`;
  - CI no Windows (Python 3.11 e 3.13) e no Linux.

  Detalhes em [docs/VALIDACAO_BETA2.md](docs/VALIDACAO_BETA2.md).
- **Auditoria de publicação** (`scripts/audit_publication.py`): procura arquivos do jogo, credenciais, dados pessoais e
  texto original no histórico Git e na árvore de trabalho.
- **Tradução:** igual à da 0.1.0-beta.1.

## [0.1.0-beta.1] — release candidata (não publicada)

- **Tradução integral:** 5.786 de 5.786 textos traduzíveis.
  - Diálogos e narrativa: 3.531, incluindo todos os finais.
  - Interface: 1.102.
  - Itens: 838.
  - Habilidades: 315.
- Enigmas adaptados com as respostas preservadas; nomes de itens e habilidades consistentes no jogo todo.
- **Instalador para Windows** (`.exe`, sem precisar de Python):
  - detecta a Steam;
  - confere build e hashes;
  - gera a tradução a partir dos arquivos do próprio jogador;
  - instala só em `Documentos\Underkeep\mods\base`;
  - desinstala pelo manifesto.
- **Ferramentas de localização em Python:**
  - leitura e regravação exata dos formatos de texto do jogo;
  - catálogo com hashes e estados de revisão;
  - validador de marcação, glifos e comprimento;
  - pack-sombra transacional.
- Guia de localização, glossário e modelos de contribuição.
