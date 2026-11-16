# Changelog

Histórico de mudanças por versão do Underkeep PT-BR. Notas para jogadores: [RELEASE_NOTES.md](RELEASE_NOTES.md).

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
