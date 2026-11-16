# Licenciamento, direitos autorais e riscos

> Este documento não é parecer jurídico. Ele registra as escolhas de licença do projeto, os limites delas e os riscos
> que continuam existindo.

## 1. Licenças do projeto

| Material | Licença | Arquivo |
|---|---|---|
| Código-fonte próprio: `ukloc/`, `scripts/`, `tests/`, `release/`, configuração | **MIT** | [`LICENSE`](../LICENSE) |
| Traduções em português (`l10n/pt-BR/`) e documentação autoral | **CC BY-NC-SA 4.0** | [`LICENSE-TRADUCAO.md`](../LICENSE-TRADUCAO.md) |
| Avisos: não oficial, direitos do jogo, uso de IA, gratuito | — | [`AVISO_LEGAL.md`](../AVISO_LEGAL.md) |
| Executáveis Windows | MIT para o código do projeto, mais as licenças do Python (PSF) e do PyInstaller (GPL com exceção para executáveis gerados) | `licencas/` no ZIP |

- **Crédito coletivo:** Contribuidores do Underkeep PT-BR.
- **Nos pacotes:** os dois levam `licencas/` com a licença MIT, a CC BY-NC-SA 4.0 e o aviso legal. A auditoria do build
  exige esses arquivos.

## 2. Por que essa separação

- **MIT para o código:** é simples, compatível com qualquer uso e adequada a ferramentas. O código do projeto é
  inteiramente próprio: ele lê os formatos do jogo para interoperabilidade, mas não contém código, dados nem texto do
  jogo.
- **CC BY-NC-SA 4.0 para a tradução e a documentação:**
  - **NC** (não comercial) é coerente com um projeto gratuito;
  - **SA** (compartilha igual) mantém abertas as melhorias feitas por terceiros;
  - **BY** garante o crédito aos tradutores.
- **Separação por tipo de material:** licenças Creative Commons não são recomendadas para software, e a MIT não é
  pensada para textos criativos.

## 3. Limites: o que nenhuma licença do projeto resolve

1. **A tradução é obra derivada.** Pela Lei 9.610/98, art. 29, a tradução depende de autorização prévia e expressa
   do autor da obra original. A Convenção de Berna (art. 8) garante esse direito exclusivo em todos os países
   signatários. As licenças do projeto valem só para a contribuição própria dos tradutores e **não autorizam** a
   tradução em si. O texto da CC 4.0 deixa claro que o licenciante só licencia os direitos que tem.
2. **Nenhum direito sobre o jogo.** Os textos originais, nomes, termos próprios, marcas e assets continuam sendo da
   Rake in Grass. Os catálogos têm IDs de texto e hashes do jogo, dados técnicos usados para interoperabilidade. O
   repositório não traz o texto original: só citações pontuais de uma frase, para justificar escolhas editoriais.
3. **Conteúdo gerado com IA.** O primeiro rascunho de grande parte das traduções foi gerado por IA e depois editado sob
   supervisão humana: glossário, decisões editoriais, revisões e playtests.
   - No Brasil, a Lei 9.610/98, art. 11, considera autor a pessoa física criadora. Nos EUA, o Copyright Office não
     registra conteúdo sem autoria humana.
   - Por isso, parte das traduções pode não ter proteção autoral, e a licença vale "na medida em que existam direitos".
4. **Instalador que gera o pack localmente.** Não distribuir arquivos do jogo elimina o risco de redistribuir assets e
   o executável. Ainda assim, o texto traduzido é distribuído, e o ponto 1 continua valendo.
5. **Interoperabilidade.** A documentação técnica descreve formatos de arquivo e o comportamento observável do jogo,
   sem código decompilado.

## 4. Contato com o estúdio e riscos

- **Contato prévio:** a Rake in Grass **não foi contatada** antes da publicação. Não houve autorização, e a ausência de
  contato ou de objeções **não é autorização**.
- **Natureza do projeto:** é publicado como iniciativa gratuita, comunitária, independente e não oficial.
- **Canal para os titulares:** existe um canal claro para pedidos, descrito no README, na seção "Titulares de
  direitos".

| Risco | Nível | Mitigação |
|---|---|---|
| Distribuir a tradução sem autorização expressa do titular | **médio** (projetos de fãs costumam ser tolerados, mas a tolerância não é direito) | projeto gratuito e não comercial; nenhum arquivo do jogo; avisos de não afiliação; canal para titulares; compromisso público de atender a pedidos de alteração ou retirada |
| Pedido de retirada (DMCA ou notificação do estúdio) | baixo a médio | retirar prontamente a release e o conteúdo apontado; manter cópia privada para eventual acordo |
| Uso indevido da marca "Underkeep" | baixo | nome descritivo ("Underkeep PT-BR"), aviso de não afiliação, sem logotipos nem capturas oficiais |
| Executáveis sem assinatura vistos como suspeitos | baixo (reputacional) | SHA-256 publicado, código-fonte aberto, build reproduzível |
| Terceiros redistribuindo versões alteradas, inclusive com malware | baixo | baixar só da página oficial; `.sha256`; aviso no README |

## 5. Contribuições

- Contribuições entram sob as mesmas licenças: MIT para código e CC BY-NC-SA 4.0 para traduções e documentação. Ver
  `CONTRIBUTING.md` e o checkbox do modelo de pull request.
- Quem usar IA para redigir uma tradução deve revisá-la e mencionar isso no PR.
- Nunca aceitar arquivos do jogo, dumps, texto original em massa nem saves.
- Mudar de licença no futuro exigiria a concordância dos contribuidores.
