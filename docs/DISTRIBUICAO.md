# Cuidados com distribuição e direitos

- Este projeto não é oficial e não reivindica direitos sobre o jogo.
- Não publicar binários ou arquivos originais, assets, fontes, saves, strings completas ou dumps do jogo no
  repositório, em issues, no CI ou em releases.
- Priorizar geradores aplicados localmente pelo jogador: o pacote de release não contém arquivos do jogo, e a tradução
  é gerada a partir da instalação do próprio jogador.
- Nunca contornar DRM nem proteção de acesso; não redistribuir conteúdo comercial.
- **Licenças:** código próprio em MIT (`LICENSE`); traduções e documentação em CC BY-NC-SA 4.0
  (`LICENSE-TRADUCAO.md`), só na medida dos direitos dos contribuidores. Nenhuma delas concede direitos sobre o jogo
  nem equivale a uma autorização da Rake in Grass. Análise e riscos: `docs/LICENCIAMENTO_E_PUBLICACAO.md`.
- **Pacotes:**
  - os dois levam `licencas/` com as licenças do projeto e o aviso legal;
  - o pacote Windows também leva as licenças do Python e do PyInstaller;
  - o pacote Steam Deck contém só o código-fonte do instalador, os catálogos e textos próprios, e a tradução é gerada
    dentro do prefixo Proton do jogador.
- **Antes de cada release:** rode `scripts/audit_publication.py` (todo o histórico Git) e a auditoria de pacote de
  `scripts/build_release.py`. Ver `docs/DESENVOLVIMENTO.md`.
- **Pedidos de titulares de direitos** são tratados com prioridade (ver README, seção "Titulares de direitos").
