# Glossário PT-BR — Underkeep

Estado dos termos: **aprovado** (validado pelo usuário, inclusive em jogo) · **provisório** (proposto na Fase 1C-B,
aguardando revisão) · **em aberto** (sem contexto suficiente; não decidir ainda).

Os termos provisórios só se tornam definitivos após revisão humana e, para termos narrativos, após ver o contexto no
jogo. O catálogo (`l10n/pt-BR/*.json`) referencia estes termos no campo `terminology` de cada entrada.

## Interface e menus

| Original (EN) | PT-BR | Estado | Contexto / observação |
|---|---|---|---|
| New Game | Novo Jogo | **aprovado** (1C-A, teste visual) | Botão do menu principal (`menu_new_game`) |
| Continue | Continuar | provisório | Menu principal |
| Load Game | Carregar Jogo | provisório | Menu principal |
| Save Game | Salvar Jogo | em aberto | Menu de pausa (não incluído na amostra) |
| save file / save | jogo salvo (ou "save" informal: evitar) | provisório | Diálogos de salvamento. "Partida salva" é alternativa |
| Options | Opções | provisório | Menu principal |
| Settings (Video/Audio/Game/Accessibility Settings) | Configurações (de Vídeo/de Áudio/de Jogo/de Acessibilidade) | provisório | Submenus de Opções |
| Credits | Créditos | provisório | — |
| Quit (para o sistema) | Sair | provisório | `menu_quit_to_system`; "Quit to Main Menu" fica em aberto |
| Back | Voltar | provisório | — |
| Language | Idioma | provisório | — |
| Master Volume | Volume Geral | provisório | — |
| Windowed | Em Janela | provisório | Modo de exibição |
| Borderless / Exclusive Fullscreen | Tela Cheia sem Bordas / Tela Cheia Exclusiva | em aberto | Não incluídos na amostra |
| Performance (modo) | Desempenho | provisório | Modo sem bordas |
| On / Off | Ligado / Desligado | provisório | Interruptores binários (ex.: V-Sync) |
| Enabled / Disabled | Ativado / Desativado | provisório | Opções do tipo habilitar/desabilitar |
| tooltip | dica | provisório | "Item tooltip" → "dica do item" |
| screen tearing | cortes na imagem (tearing) | provisório | Jargão técnico entre parênteses na primeira ocorrência |
| delete | excluir | provisório | Ação destrutiva em saves |

## Mecânicas de RPG

| Original (EN) | PT-BR | Estado | Contexto / observação |
|---|---|---|---|
| damage | dano | provisório | "2 damage" → "2 pontos de dano" em descrições; "dano de fogo" em rótulos |
| fire / ice / lightning / poison damage | dano de fogo / gelo / raio / veneno | provisório (fogo); em aberto (demais) | Só "fogo" aparece na amostra |
| round (combate) | rodada | provisório | **Distinto de turn** |
| turn | turno | em aberto | Atenção: "Turn Animation" refere-se a girar a câmera ("Animação de Giro"?) |
| caster | conjurador | provisório | Quem lança a magia |
| spell | magia | em aberto | Alternativa: feitiço |
| skill | habilidade | em aberto | — |
| Bleeding | Sangramento | provisório | Efeito de status |
| Burn (status) / burn (verbo) | Queimadura / queimar | em aberto (status) | O verbo foi usado em `skill_fire_spark_summary` |
| Freeze / Stun / Poison (status) | Congelamento / Atordoamento / Envenenamento | em aberto | Definir junto com os ícones/estados do jogo |
| chance | chance | provisório | "{x} de chance de…" |
| mana / stamina / health | mana / vigor? / vida | em aberto | Verificar a HUD antes de decidir |
| Zeal | (manter?) | em aberto | Recurso próprio do jogo; decidir com contexto |
| party | grupo | em aberto | "Create Party" → "Criar Grupo"? |
| hero | herói / heroína | em aberto | Requer cuidado de gênero (ver guia) |

## Mundo e narrativa

| Original (EN) | PT-BR | Estado | Contexto / observação |
|---|---|---|---|
| Underkeep | Underkeep | **mantido** (nome próprio) | Vilarejo / título do jogo |
| village | vilarejo | provisório | "Aldeia" soa europeu ou indígena no Brasil |
| summons (substantivo) | convocação | provisório | — |
| tavern | taverna | provisório | — |
| Nomes de personagens, armas lendárias, reinos (ex.: Bastion, Veyra, Shardpiercer) | **não traduzir por ora** | em aberto | Decidir caso a caso (ver guia, nomes próprios) |
| Nomes de habilidades (ex.: Fire Spark) | **não traduzir por ora** | em aberto | Exigem decisão editorial conjunta |

## Adições do lote 01 (Fase 1D, provisórios)

| Original (EN) | PT-BR | Observação |
|---|---|---|
| champion | campeão | Membro do grupo (How to Play) |
| quest | missão | "Quests" → "Missões" |
| Shrine / Revival Statue | Santuário / Estátua da Ressurreição | — |
| Reach (propriedade de arma) | Alcance | "Out of Reach" → "Fora de Alcance" |
| alcove | nicho | — |
| cooldown | recarga | — |
| Zeal | Fervor | ES também usa "fervor" |
| Stamina / Health | Vigor / Vida | Mana mantém "Mana" |
| craft / ingredients / recipes | criar / ingredientes / receitas | Alquimia |
| Pick / Grab / Drop / Throw | Pegar / Segurar / Largar / Lançar | Comandos de item |
| Controls / Controller, Gamepad | Comandos / Controle | Evita "Controles" × "Controle" |
| Quick Save / Quick Load (ação) | Salvar Rápido / Carregar Rápido | Espaço de save: "Salvamento Rápido" |
| Stoneborns, Slugmen, Ravens, Elks | Nascidos da Pedra, Homens-Lesma, Corvos, Alces | Raças jogáveis |
| lockpick / pickaxe / chisel / shovel | gazua / picareta / cinzel / pá | — |
| turn (girar) | virar / giro | "Turn Left" → "Virar à Esquerda"; "turn-based" → "por turnos" |

## Adições do lote 02 (Fase 1E, provisórios)

Diretriz 1E: **caixa de frase** em menus, rótulos e nomes de efeito (exceto nomes próprios: Caerlin, Zerethic,
Godzilla, Fervor como recurso). Os lotes 01 e 1C-B ainda usam caixa de título (pendente de conversão).

| Original (EN) | PT-BR | Observação |
|---|---|---|
| Burn / burning / burn (verbo) | Queimadura / em chamas / queimar | Rótulos usam o substantivo (sem marca de gênero) |
| Freeze / frozen | Congelamento / congelado | "Você sofre congelamento" (neutro) |
| Stun / stunned | Atordoamento / atordoar | Linhas com o termo isento de aviso de comprimento (justificado) |
| Poison / poisoned | Veneno / Envenenamento / envenenar | — |
| Bleed / bleeding | Sangramento / sangrando | — |
| Disease / diseased | Doença / doente | "{name} adoeceu!" |
| Blind(ness) / Paralyzed | Cegueira / Paralisia | — |
| Strength / Dexterity / Endurance / Wisdom | Força / Destreza / **Constituição** / Sabedoria | Endurance ≠ Resistance (resistências) ≠ Stamina (Vigor) — **decisão editorial** |
| HP / Hit Points | PV / pontos de vida | — |
| Evasion / Armor / Critical Chance | Esquiva / Armadura / Chance de crítico | — |
| Fire/Ice/Lightning/Blood Magic/Poison Resistance | Resistência a fogo/gelo/raio/magia de sangue/veneno | — |
| Sharpness | Afiação | Propriedade de arma (provisório) |
| Racial Trait / Stable / Unstable Mutation | Traço racial / Mutação estável / instável | "(Rare)" → "(rara)" |
| Voidcaller | Invocador do Vazio | Classe (provisório) |
| Paladin | Paladino | — |
| Nomes de efeitos, traços e mutações | traduzidos de forma descritiva (ex.: Pacto de sangue, Inquilino do vazio) | **Provisório**: aguardam a decisão sobre nomes de habilidades |

## Decisões aprovadas (Fase 1F)

Endurance → Constituição · Resistance → Resistência · Stamina → Vigor · Voidcaller → Invocador do Vazio ·
Sharpness → Afiação (provisório) · HP → PV (Pontos de Vida) · Burn → Queimadura · Freeze → Congelamento ·
Stun → Atordoamento. Caixa de frase em todos os rótulos (lotes anteriores padronizados).

## Adições do lote 03 (provisórios)

| Original (EN) | PT-BR | Observação |
|---|---|---|
| Ranger / Warrior / Wizard / Thief / Paladin / Blood Mage | Patrulheiro / Guerreiro / Mago / Ladrão / Paladino / Mago de sangue | Classes |
| Human / Dwarf / Stoneborn / Raven / Elk / Slugman | Humano / Anão / Nascido da pedra / Corvo / Alce / Homem-lesma | Raças (**provisório**, aguardam decisão) |
| Main Stat | Atributo principal | — |
| Apparel (categoria) | Acessórios | Anéis, amuletos, vestuário |
| Armor pierce | Perfuração de armadura | — |
| Lucky (duas rolagens de dano) | Sorte | "têm Sorte" |
| Void Mend | Remendo do vazio | Nome de habilidade (provisório) |
| Quest Item | Item de missão | — |
| Cooldown (rótulo) | Recarga | — |
| Tipos de item | Espada, Adaga, Machado, Maça, Cajado, Arco, Escudo, Anel, Amuleto, Armadura, Cinto, Elmo, Luvas, Botas, Manto | — |

## Adições do lote 04 — skills (provisórios)

Nomes de habilidade seguem os nomes de efeito já usados em `common` (ex.: Presa do caçador, Pacto de sangue,
Barreira protetora, Guarda divina), garantindo o mesmo termo em ambas as telas.

| Original (EN) | PT-BR | Observação |
|---|---|---|
| Fire Spark / Static Shock / Ice Shard / Fireball | Centelha de fogo / Choque estático / Estilhaço de gelo / Bola de fogo | Mago |
| Quickshot / Aimed Shot / Deadly Shot | Disparo rápido / Disparo mirado / Disparo mortal | Patrulheiro |
| Lay on Hands / Judgment / Righteous Strike | Imposição de mãos / Julgamento / Golpe justo | Paladino |
| Exsanguinate / Leechcraft / Bloodfall | Exsanguinar / Arte da sanguessuga / Chuva de sangue | Mago de sangue |
| Cleave / Riposte / Shield Bash | Talho / Réplica / Golpe de escudo | Guerreiro |
| caster | conjurador | — |
| Lifesteal | roubo de vida | — |
| Usable only with … | Só pode ser usada com … | Requisito de arma |
| Does not consume an action | Não consome ação | — |
| Lv. N | Nv. N | Níveis de habilidade |
| Recast | repetir / recriação | Conforme contexto |

## Adições do lote 05 — items, 1ª metade (provisórios)

Nomes de item em caixa de frase. Nomes descritivos traduzidos; nomes próprios narrativos mantidos (Veyra, Bastion,
Dun Kareth, Valen, Lethander, Krul'Thar, Durok, Lucille, Jacob, Meren, Ordan, Selwyn, Seredin, Greywall, Lerwick, Orrem).

| Original (EN) | PT-BR | Observação |
|---|---|---|
| Rusty (prefixo / linha de efeito) | enferrujado(a)(s) / "Enferrujada." | Concorda com o item |
| Chain / Scale / Plate (armaduras) | de malha / de escamas / de placas | Chain Armor -> Cota de malha |
| Moonsteel / Embersteel | aço lunar / aço ardente | Materiais |
| of Striking (série) | do impacto | Arco, luvas, botas, elmo, manto |
| Whispering (série) | sussurrante(s) | Armadura, luvas, botas |
| Ironveil / Arrowcatcher | do véu de ferro / apanha-flechas | — |
| Archmage / Archmage Academy | arquimago / Academia dos Arquimagos | — |
| Sleeper / the Circle | Adormecido / o Círculo | Monstro e facção (conferir em `game`) |
| Great Axe / Quarterstaff / Maul / Buckler | Machadão / Bordão / Malho / Broquel | — |
| Potion of (Minor) Healing / Stamina / Mana | Poção de cura / vigor / mana (menor) | Mega Healing -> megacura |
| Potion of Cure Poison | Poção contra veneno | Corrige "Poción contra el veneno" |
| Frostvein / Thunderwake / Ghoststep (Draught) | Trago gélido / Trago do trovão / Trago do passo fantasma | — |
| Warblood Tonic / Mindwell Elixir / Wardstone Elixir | Tônico sangue de guerra / Elixir da lucidez / Elixir da pedra protetora | — |
| Ironhide Potion / Voidshard / Caerlin Essence | Poção pele de ferro / Fragmento do vazio / Essência de Caerlin | — |
| Mortar and Pestle | almofariz e pilão | Ferramenta de alquimia |
| Recipe "Potion of X" | nome do produto | Receita e poção com o mesmo nome |
| Health / Stamina / Mana restored | Vida restaurada / Vigor restaurado / Mana restaurada | Linhas de efeito |
| "X deals N damage for N rounds" | "X causa N pontos de dano por N rodadas" | Linhas de efeito das armas |
| Mushroom Stew / Dungeon Toast | Ensopado de cogumelos / Torrada da masmorra | — |

## Adições do lote 06 — items, 2ª metade (provisórios)

Nomes próprios mantidos: Caerlin, Khelebar, Jacob, Bogrin, Durgan, Michael, Juran, Ixarion, Maltherion, Thalric,
Zerethic, Barlo, Grgla, Daroou, Balduran, Hulk e os nomes inventados de cogumelos Shreemer e Pippa.

| Original (EN) | PT-BR | Observação |
|---|---|---|
| Moonpetal / Solarbloom / Amberrose | Pétala lunar / Flor solar / Rosa âmbar | Ingredientes; "moonpetal" também no caderno |
| Caerlin Blue Bloom / Caerlin Blossoms | Flor azul de Caerlin / flores de Caerlin | Ingrediente da Essência de Caerlin |
| Sunnybell / Frostwick / Dirtfather | Campainha solar / Pavio gélido / Padrinho da terra | Cogumelos do Barlo |
| Minor / Major (cintos e anéis) | menor / maior | Cinto da esquiva menor |
| -bane (Beastbane, Corpsebane, Gravebane) | flagelo das feras / dos cadáveres / dos túmulos | — |
| Signet | sinete | — |
| High Cleric | Sumo Clérigo | Chaves douradas |
| Runic Segment | segmento rúnico | Partes da chave de Underkeep |
| Waystone | pedra de passagem | Conferir em `game` |
| the Source | a Fonte | Carta de Jacob; conferir em `game` |
| Mortar and Pestle | Almofariz e pilão | Nome do item (caixa de frase) |
| Lockpick Tools | Gazuas | — |

## Termos narrativos consolidados (lote 07, `game`)

Verificados no texto de `game`. Continuam *provisórios* até a revisão humana, mas deixam de depender de confirmação.

| Original (EN) | PT-BR | Natureza (evidência) |
|---|---|---|
| the Source | a Fonte | Entidade: ser pulsante no mausoléu, alimentado pela Ordem do Sangue (missão de Jacob) |
| Waystone | pedra de passagem | Pedra de viagem rápida; a pedra de teletransporte a ativa (Khelebar) |
| Waygate (termo do Khelebar) / stone gates, stone portals | portal de passagem / portais de pedra | Mesma rede de viagem, nas palavras do Khelebar |
| High Cleric | Sumo Clérigo | Título de Maltherion (encontro no mausoléu) |
| Sleeper | Adormecido | Tipo de inimigo ("Crimson Sleeper" = acólito de sangue) |
| the Circle | o Círculo (facção, `items`) / o círculo (ritual, `game`) | Em `game` só aparece "Break the Circle." no pentagrama: círculo ritual |
| Blood Order | Ordem do Sangue | Facção (seita no cemitério) |

## Adições do lote 07 — `game`: introdução e vilarejo (provisórios)

Nomes próprios mantidos: Torren, Barlo Winch, Ronan, Khelebar, Jacob, Aldren, Garric, Garrel, Durok, Grimfen.
Lugares: o nome inventado é mantido e o substantivo genérico é traduzido.

| Original (EN) | PT-BR | Observação |
|---|---|---|
| Fangroot Forest | Floresta de Fangroot | — |
| Caerlin Woods | Bosques de Caerlin | Igual a `items` ("bosques de Caerlin") |
| Duskhollow (Woods/forest) | Bosques de Duskhollow | — |
| Underkeep Tower / the Tower | Torre de Underkeep / a Torre | Maiúscula quando é "a Torre" do enredo |
| Underkeep Cemetery | Cemitério de Underkeep | — |
| The Crooked Wing | A Asa Torta | Taverna; o nome vem do corvo de asa torta |
| Mayor (Aldren) | prefeito Aldren | — |
| Treasure March | Marcha do Tesouro | Apelido do Barlo para a expedição anã |
| teleportation stone | pedra de teletransporte | Igual a `items` |
| mushroom kin / mushroomlings | criatura-cogumelo, família / cogumelinhos | Criatura tratada no feminino |
| burrowers | escavadores | Conferir com o nome do inimigo |
| ranger (Jacob) | patrulheiro | — |

## Adições do lote 08 — Aldren, Fangroot e nomes de áreas (provisórios)

Nomes de área: o nome inventado é mantido (Grimfen, Blackwoods, Mireheart, Rootgrave, Hollowgrave, Gravewood,
Blightvein, Elderfen, Obula) e o genérico é traduzido. Lugares descritivos ficam em caixa de frase ("Ninho de ratos",
"Covil dos lobos"). Nomes com título ficam com maiúsculas ("Santuário da Última Chama", "Celas dos Esquecidos").

| Original (EN) | PT-BR | Observação |
|---|---|---|
| Burrower | Escavador | Confirmado: criaturas que "roem o chão" ao sul do vilarejo; nome do inimigo alinhado |
| Soulforge - East/West Garden, Outer Halls | Forja das Almas - Jardim Leste/Oeste, Salões Externos | Igual a `items` (Forja das Almas) |
| Tower Level N / Tower Entrance | Torre - nível N / Entrada da Torre | — |
| Outer Underkeep Tower (viagem rápida) | Exterior da Torre | Encurtado para caber |
| Rat Queen | Rainha dos Ratos | — |
| Garric the Gatekeeper | Garric, o Porteiro | — |
| Echo Sight / Infravision | Visão por eco / Infravisão | Igual a `common` |
| Mayor | prefeito | Minúscula antes do nome ("o prefeito Aldren") |
| tripwire | armadilha de fio | — |

## Adições do lote 09 — Caerlin e Blightvein (provisórios)

| Original (EN) | PT-BR | Observação |
|---|---|---|
| Caerlin, the Wolf Queen | Caerlin, a Rainha dos Lobos | Semideusa da estátua; nome próprio mantido |
| Whispering Tree | Árvore Sussurrante | Local (nome próprio) |
| Huntclaw (inimigo) | Rasgador | Encurtado para o espaço do nome |
| key fragment / shard (Torren) | fragmento da chave | Item: segmento rúnico (`items`) |
| tincture / vial (Torren) | frasquinho, frasco | Item: Tintura desconhecida (`items`) |
| Anvil of Creation | Bigorna da Criação | Forja das Almas |
| Lord of the Tower | Senhor da Torre | — |
| wyrm | serpe | Distinto de "dragon" (dragão) |
| hunting trap | armadilha de caça | — |
| crystal entity | entidade de cristal | Chefe da mina |

## Adições do lote 10 — cemitério, mausoléu e arredores da Torre (provisórios)

| Original (EN) | PT-BR | Observação |
|---|---|---|
| High Cleric / high priests | Sumo Clérigo / sumos clérigos | Título de **três** clérigos da Ordem do Sangue (Maltherion, Thalric, Zerethic), guardiões das três chaves |
| Maltherion the Sleepless Watcher | Maltherion, o Vigia Insone | Inimigo |
| Thalric the Undying Flame | Thalric, a Chama Imortal | Inimigo |
| Zerethic the Heart Eater | Zerethic, o Devorador de Corações | Inimigo |
| Ixarion the Bloodbound Herald | Ixarion, Arauto do Sangue | Encurtado para caber |
| Crimson Sleeper | Adormecido carmesim | Tipo de inimigo (acólito de sangue) |
| He Who Watches / Crimson Witness | Aquele que Vigia / Testemunha Carmesim | Entidade cultuada pela Ordem do Sangue |
| Senha: "The blood of He Who Watches still feeds the roots." | "O sangue d'Aquele que Vigia ainda alimenta as raízes." | Texto **idêntico** na pista, na escolha da porta e no diário |
| the One Below / the Bound / True Name | Aquele que Habita Abaixo / o Aprisionado / Nome Verdadeiro | Ritual de Ixarion |
| summoning / binding circle | círculo de invocação / de aprisionamento | Círculo ritual (minúscula); a facção "o Círculo" segue só em `items` |
| bloodmonk / cultists | monge de sangue / cultistas | — |
| Follower of the Old Ways | Seguidor dos Antigos Caminhos | Jacob |
| Feather of Mercy | Pena da Misericórdia | — |
| ward / seal (Torre) | proteção / selo | Quatro obeliscos sustentam o selo da Torre |

## Adições do lote 11 — Duskhollow e acampamento anão (provisórios)

Nomes próprios mantidos: Durok Stonevein, Korr, Brenna Ironsong, Grumli Ironbeard, Snorri Kegsson, Dun Kareth, clãs
Stonehammer e Ironpeak.

| Original (EN) | PT-BR | Observação |
|---|---|---|
| Captain of the guard / warleader (Korr) | capitão da guarda / líder de guerra | — |
| Durok's Promise | Promessa de Durok | Igual a `items` |
| firstborn of the Soulforge | primogênito da Forja das Almas | Machado; igual a `items` |
| Moonsteel (Ore) | aço lunar (minério de aço lunar) | Igual a `items` |
| Dwarven Helm / Gauntlets / Boots / Shield / Armor (forja) | elmo anão / manoplas anãs / botas anãs / escudo anão / armadura anã | Itens resultantes: "de aço lunar" em `items` |
| Hard Cave-ins / Gold Veins | desmoronamentos duros / veios de ouro | Ofícios ensinados por Brenna |
| (Dwarven) Golden Chisel / Pickaxe | cinzel dourado (anão) / picareta | Igual a `items` |
| Forgebrew | cerveja da forja | Igual a `items` |
| powder / fuse / charge | pólvora / pavio / carga | Plano de Korr |
| the old shaft | o poço velho | — |

## Adições do lote 12 — covil do dragão, Forja das Almas e inimigos (provisórios)

Nomes de inimigo em caixa de frase, curtos (o slot do ES é estreito). Nomes próprios mantidos: Obula, Torren Malik,
Lady Puffella, Sir Moldsworth, Arachneira, Maxi Nunik.

| Original (EN) | PT-BR | Observação |
|---|---|---|
| wyrm / dragon | serpe / dragão | Mesma criatura; "serpe" nas falas de Durok, Korr e no diário |
| Soul Warden / Spirit Lantern / Voidshard | Guardião das almas / lanterna espiritual / fragmento do vazio | Igual a `items` |
| Boneblade (Archer, Eternal) / Voidblade | Osso-gume (Osso-arqueiro, Osso-gume eterno) / Fio-vazio | Esqueletos |
| Wrathclaw / Grassfang / Demonclaw | Garra-fúria / Víbora / Demogarra | — |
| Bogmaw / Frog King, Last Crown of the Mire | Sapão / Rei Sapo, Última Coroa do Lodaçal | Grimfen |
| Rat Queen, Mother of the Warren | Rainha dos Ratos, Mãe da Toca | — |
| Archmage of the Underkeep | Arquimago de Underkeep | — |
| Fountain (inimigo/objeto) | Chafariz | Evita confusão com "a Fonte" (the Source) |
| Cursed Digger | Cavador amaldiçoado | "Escavador" fica reservado a Burrower |
| Test of Courage / Dexterity | Prova de Coragem / de Destreza | Salas da Forja |
| Master Lever / Incinerator Unit | alavanca-mestra / incinerador | — |
| Seal of Yellow / Purple | Selo amarelo / roxo | — |

## Adições do lote 13 — Grimfen (provisórios)

| Original (EN) | PT-BR | Observação |
|---|---|---|
| Grgla the Sleazy | Grgla, o Sórdido | Fala em 3ª pessoa, frases curtas ("Grgla sabe.") |
| Fog Maze / Misty Maze | Labirinto de Névoa / Labirinto enevoado | Direções: leste, sul, norte |
| Grgla's Fish | peixe de Grgla | Igual a `items` |
| Frog King / King of the Mire | Rei Sapo / Rei do Lodaçal | — |
| Mushroom Men / the Colony / mycelium | Homens-cogumelo / a Colônia / micélio | — |
| mire / bog / swamp | lodaçal / brejo / pântano | — |
| mire fountain / bloodstained fountain | chafariz do lodaçal / chafariz manchado de sangue | "Chafariz", como o inimigo; nunca "fonte" (reservado à Fonte) |
| The Thing (chefe do pântano) | a Coisa | Fala arrastada ("Chhheiro... booom...") |
| Obula / the Old One | Obula / o Antigo | "Old One" ambíguo no original |
| marshfolk | povo do brejo | — |
| Korr Stonehammer | Korr Stonehammer | Sobrenome = clã Stonehammer |

## Adições do lote 14 — Torre, mago, Torren Malik e desfechos (provisórios)

| Original (EN) | PT-BR | Observação |
|---|---|---|
| the gate (sob a Torre) | o portão | Igual a `quest_underkeep_main_quest_22` |
| the portal / crimson veil | o portal / o véu carmesim | Arco de luz vermelha diante de Torren |
| the wizard / Lord of the Tower | o mago / o Senhor da Torre | Fala em CAIXA ALTA (`{color_ancient_voice}`), trata o grupo por "vocês" |
| the Architect | o Arquiteto | Epíteto de Torren no desfecho |
| Soulcleaver / Soulforge Axe | Fende-almas / machado da Forja das Almas | Nome do item em `items` |
| Torren's Tincture | tintura de Torren | Item "Tintura desconhecida" |
| The Last Guardian | o Último Guardião | O gigante; livro "O último guardião" |
| the four guardians / keys / seals | os quatro guardiões / chaves / selos | — |
| The Tower's Seal (missão) | O selo da Torre | Fragmentos da chave e quatro arcos |
| apparition / projection | aparição / projeção | Imagem do mago nas provações |
| Gallery / Dark Room | Galeria / Sala escura | Placas da Torre |
| the Source (placas da Torre) | a Fonte | "COM O TEMPO, O HOMEM SE TORNOU A FONTE" |
| THE END / Thanks for playing | FIM / Obrigado por jogar | Encerramento |
| Enigmas das lápides | cinzas, adaga/lâmina, pena (corvo/anjo), moeda | Respostas preservadas; rima adaptada |


## Adições da Fase 2A — patch 1.0.6 (provisórios)

| Original (EN) | PT-BR | Observação |
|---|---|---|
| scale with Strength / Dexterity (armas) | baseada(s) em Força / Destreza; "se baseia em" | Evita o anglicismo "escalar com" |
| Base attributes / Base stats | atributos base | Não aumentam ao subir de nível |
| Potion of Forgetfulness (respec) | Poção do esquecimento | Devolve os pontos de habilidade gastos |
| Refunds (pontos) | devolve | "Devolve todos os pontos de habilidade gastos." |
| Cloak of Shadows (habilidade do Ladrão) | Manto das sombras | Igual ao item `item_cloak_of_shadows`; o Patrulheiro segue com "Manto da agilidade" |
| Melee / Ranged critical hit chance | Chance de crítico corpo a corpo / à distância | Linhas de atributo do item |
| Armor Piercing | Perfuração de armadura | Já usado em `item_info_part_damage4` |
| Tavern (rótulo do mapa) | Taverna | Demais rótulos do mapa são nomes próprios (Aldren, Barlo, Ronan, Khelebar) |
