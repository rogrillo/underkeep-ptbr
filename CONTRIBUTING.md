# Como contribuir com o Underkeep PT-BR

Obrigado pelo interesse! Este é um projeto comunitário e não oficial. Toda ajuda é bem-vinda: apontar erros,
sugerir traduções melhores, testar o jogo ou melhorar as ferramentas.

## Regra número um: nada de arquivos do jogo

**Nunca envie**, em issues, pull requests, comentários ou anexos:

- arquivos do Underkeep (`.rfile`, `.db`, `underkeep.exe`, texturas, sons, fontes), packs gerados ou pastas `mods`;
- dumps, planilhas ou listas com o texto original extraído em massa;
- saves, `game_config.txt`, logs com caminhos pessoais, credenciais ou dados pessoais.

Citar **uma frase curta** do original para identificar um problema é aceitável. Capturas de tela com o texto em
questão também são.

## Abrir uma issue

Na aba **Issues → New issue**, escolha um modelo:

| Modelo | Quando usar |
|---|---|
| Problema de tradução | erro, frase pouco natural, termo inconsistente, gênero/número errado, texto cortado |
| Bug técnico | falha ao instalar, desinstalar ou carregar o jogo |
| Sugestão de melhoria | ideias para o projeto, documentação ou ferramentas |

Antes, procure se já existe uma issue parecida. Informe sempre a versão da tradução (por exemplo, `0.1.0-beta.2`) e a plataforma (Windows ou Steam Deck).

## Propor uma mudança de tradução

- **Sem programação:** abra uma issue "Problema de tradução" com o texto atual, onde aparece e a sua sugestão.
- **Com pull request:** edite a entrada em `l10n/pt-BR/<categoria>.json` seguindo o
  [guia para tradutores](docs/CONTRIBUINDO_TRADUCOES.md), rode os testes e abra o PR com o modelo preenchido.

Decisões editoriais (tratamento do jogador, gênero, nomes próprios, termos) seguem o
[guia de localização](docs/GUIA_DE_LOCALIZACAO.md) e o [glossário](docs/GLOSSARIO.md). Para mudar uma regra ou um
termo consolidado, abra primeiro uma issue para discussão. Mudanças pontuais que contrariem o glossário sem
justificativa não serão aceitas.

## Contribuir com código

- Todo código novo é **Python 3.11+**, com testes `pytest` e sem dependência dos arquivos do jogo nos testes (use as
  fixtures sintéticas de `tests/conftest.py`).
- Não crie scripts em JavaScript/TypeScript.
- Preserve a arquitetura existente (`ukloc/`, catálogo em `l10n/pt-BR/`, pack-sombra). Não crie um sistema de tradução
  paralelo.
- Nenhuma ferramenta pode gravar na pasta da Steam. Instalação só em `Documentos\Underkeep\mods\base`, com
  verificação e reversão.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Detalhes técnicos: [docs/DESENVOLVIMENTO.md](docs/DESENVOLVIMENTO.md).

## Pull requests

- Um assunto por PR, com descrição clara do motivo.
- Preencha o checklist do modelo: testes, validador, glossário e ausência de arquivos proprietários.
- Mudanças de tradução entram como `translated` + `review_status: pending` e precisam de revisão antes de serem
  promovidas.
- Os mantenedores podem pedir ajustes ou recusar mudanças que conflitem com as decisões editoriais documentadas.

## Licença das contribuições

Ao enviar uma contribuição, você concorda em disponibilizá-la sob as licenças do projeto:
- **código:** [MIT](LICENSE);
- **traduções e documentação:** [CC BY-NC-SA 4.0](LICENSE-TRADUCAO.md).

Você também declara que a contribuição é sua, ou que tem o direito de enviá-la, e que ela não inclui material de
terceiros, como arquivos ou textos do jogo em massa. Se usou ferramentas de IA para redigir uma tradução, revise o
resultado e mencione isso na descrição do PR. Essas licenças não concedem nenhum direito sobre o Underkeep, que
pertence à Rake in Grass.

## Conduta

Seja respeitoso e construtivo. Críticas à tradução são bem-vindas; ataques pessoais, não. Lembre-se de que o jogo
pertence à Rake in Grass: não peça nem compartilhe cópias do jogo.
