---
name: resolver-questao
description: Transforma a foto de uma questão de concurso militar em um vídeo de resolução renderizado em Manim, com narração em áudio. Use quando o usuário enviar/apontar uma foto de questão e pedir para gerar a resolução, o roteiro, o áudio ou o vídeo.
---

# Resolver questão em vídeo

Pipeline completo: foto da questão → roteiro JSON → validação (gabarito + SymPy) →
áudio (Coqui XTTS-v2) → vídeo (Manim). Cada etapa só avança se a anterior passar.

Ambiente: tudo roda no conda env `no_alvo` (`conda run -n no_alvo <comando>`; veja
`README.md`/`setup.sh`/`setup.ps1` se o ambiente ainda não existir). Não existe mais
chave de API nenhuma nesse fluxo — TTS é local (XTTS-v2, CPU ou GPU conforme a
máquina).

## Passo 0 — Entrada

Aceita qualquer uma destas formas (o usuário escolhe a que for mais conveniente):

- **Foto** (jpg/png), normalmente em `fotos/` — leia com a ferramenta Read (é
  multimodal, funciona direto na imagem).
- **PDF** — Read também abre PDF (use o parâmetro `pages` se for um arquivo grande);
  serve tanto pra PDF com texto selecionável quanto pra PDF escaneado (a ferramenta
  renderiza a página como imagem nesse caso).
- **Texto colado** direto na conversa — já vem pronto, sem precisar extrair de imagem.
- **LaTeX** (arquivo `.tex` ou trecho colado) — leia como texto e interprete a
  estrutura (`\begin{enumerate}`/`\item` costuma marcar as alternativas).

Se o usuário já souber banca/ano/número/gabarito oficial, use essas informações;
senão, extraia o que der da própria fonte e pergunte o gabarito oficial se não
estiver visível — a trava de validação (passo 2) depende dele.

## Passo 1 — Ler a foto e escrever o roteiro

Leia a imagem com a ferramenta Read (ela é multimodal). Transcreva o enunciado e as
alternativas exatamente como aparecem. Depois escreva o roteiro de resolução como um
JSON no formato de `roteiro_exemplo.json` (leia esse arquivo como referência de
schema antes de escrever o primeiro roteiro da sessão). Campos obrigatórios:

- `id`: slug tipo `afa-2018-q19` (banca-ano-qNN, minúsculo, com hífen)
- `banca`, `ano`, `ordem`, `assunto`, `sub`, `gabarito`, `alternativas`
- `validacao`: escolha o `tipo` mais adequado dentre os três que `motor/validar.py`
  sabe checar — `expressao`, `equacao` ou `contagem_raizes` (releia o docstring de
  `motor/validar.py` para os campos exatos de cada tipo). Se a questão não se encaixar
  em nenhum, ok deixar um `tipo` fora dessa lista — a aritmética fica "não verificada
  automaticamente" mas o roteiro ainda pode ser aprovado pela trava de gabarito.
- `passos`: sequência de ações (`titulo`, `enunciado`, `figura`, `cabecalho`,
  `escrever`, `transformar`, `resposta`). Cada passo com `narracao` que precisa **ler
  bem em voz alta**: nunca deixe LaTeX, símbolos ou fórmulas na `narracao` — verbalize
  tudo em português (ex.: "nove meios vezes dois ao cubo", não `\frac{9}{2}\cdot2^3`).
  O TTS só recebe esse texto puro. Pontuação também importa aqui: **nunca use `:`,
  `;` nem o padrão `a)`/`b)`/`c)` dentro de `narracao`** — o XTTS-v2 às vezes lê esses
  sinais em voz alta (ex.: dois-pontos vira "dois pontos" falado). Escreva alternativas
  como "Opção á, catorze. Opção b, vinte." em vez de "a) 14. b) 20."; troque um
  dois-pontos por vírgula/"sendo"/nova frase. Repare no acento em "Opção **á**" —
  a letra A sozinha colide com a preposição "a" (átona, "engolida"), a palavra mais
  curta e fraca do português, e o XTTS às vezes lê a letra assim em vez do nome
  bem pronunciado. O acento força a pronúncia tônica certa. B/C/D não têm esse
  problema (não colidem com nenhuma palavra comum) — só a letra A precisa do acento.
  Isso vale só pra `narracao` — o campo `texto`/`alternativas` (o que aparece ESCRITO
  na tela) pode ter `:`/`a)` normalmente.

Salve em `roteiros/<id>.json` (crie a pasta se não existir).

Se a questão tiver uma figura/desenho, prefira vetorizar (SVG) em vez de colar um
PNG — `quadro.py` desenha SVG traço a traço (`Create`), o que combina muito mais com
o estilo "quadro didático" do que colar uma imagem estática. Só use PNG se não houver
como vetorizar a tempo.

### Diagramas (estilo 3Blue1Brown / MindYourDecisions)

Além de `figura` (imagem/SVG), `quadro.py` sabe desenhar 13 tipos de diagrama nativos
— vale muito mais a pena usar um destes do que descrever a mesma coisa só em texto,
quando a questão for de função, geometria, intervalo, contagem/probabilidade,
contagem de caminhos/grade, recorrência de cobertura, trigonometria, números
complexos, vetores, coordenadas polares, dados tabelados ou geometria espacial:

- `"acao": "grafico"` — plano cartesiano com até 3 funções. Campos: `funcoes`
  (lista de `{"expr": "x**2-1", "rotulo": "f(x)"}`, expressão em sintaxe SymPy),
  `dominio` `[xmin,xmax]`, `imagem` `[ymin,ymax]`, `pontos` (marca pontos), `legenda`.
- `"acao": "linha_numerica"` — reta real, ótimo pra intervalo/desigualdade/MDC-MMC.
  Campos: `dominio` `[min,max]`, `pontos` (`{"x":1,"rotulo":"1","aberto":true}` —
  bola aberta/fechada), `intervalos` (`{"de":1,"ate":4}` — trecho pintado).
- `"acao": "arvore"` — árvore de possibilidades por níveis, ideal pra combinatória e
  probabilidade (princípio multiplicativo). Campo: `niveis`, lista de listas de
  rótulos — ex. `[["3 pretos","2 vermelhos","1 branco"], ["vaga A","vaga B", ...]]`.
  Cada nó de um nível liga com TODOS os nós do nível seguinte; não dá pra desenhar
  ramificação seletiva.
- `"acao": "geometria"` — figura geométrica a partir de uma lista `elementos`
  tipados: `ponto` (`nome,x,y,rotulo`), `segmento` (`de,ate`), `circulo`
  (`centro,raio`), `poligono` (`vertices`), `angulo` (`vertice,de,ate,rotulo`).
- `"acao": "grade"` — malha (n×n por padrão) pra contagem de caminhos (Catalan,
  problema da urna/eleição, princípio da reflexão), tabuleiro, arranjo em grade.
  Campos: `n` (ou `colunas`/`linhas` pra malha retangular — útil quando um caminho
  refletido termina fora do quadrado original), `caminho` (atalho pra 1 caminho em
  destaque) ou `caminhos` (lista, pra mostrar vários ao mesmo tempo — cada item
  `{"passos":["D","C",...],"cor":"giz"|"destaque"|"apoio"|"nota","tracejado":false}`),
  `diagonal` (True desenha (0,0)-(n,n)), `linha_extra_desloc` (reta paralela à
  diagonal, deslocada N células — ex. `1` pra y=x+1, a reta que separa caminho bom de
  ruim), `sombrear` (`"acima"`/`"abaixo"`), `pontos` (`{"i":1,"j":2,"rotulo":"P"}` —
  marca um ponto específico, ex. onde a reflexão começa). Pra ilustrar o princípio da
  reflexão de verdade (não só em texto): mostre o caminho ruim e o refletido juntos,
  com cores diferentes, um deles tracejado, e o ponto de reflexão marcado — foi assim
  que o roteiro de exemplo de Catalan (`roteiros/catalan-caminhos-n4.json`) resolveu.
- `"acao": "tabuleiro"` — tabuleiro `linhas`×`colunas` coberto por peças de dominó
  1×2, pra recorrência de cobertura (tipo Fibonacci — "de quantos jeitos cobrir um
  tabuleiro 2×n"). Campo `pecas`: lista de `{"col":0,"linha":0,"orientacao":"V"|"H"}`
  ((col,linha) é a célula inferior-esquerda da peça, 0-based); as peças precisam
  cobrir o tabuleiro certinho, sem sobrepor nem deixar buraco.
- `"acao": "ciclo_trigo"` — círculo trigonométrico, pra inequação trigonométrica,
  arco côngruo, simetria de sinal entre quadrantes. Campos: `angulos` (lista de
  `{"rad":"pi/3","rotulo":"\\pi/3"}`, `rad` em radianos, sintaxe SymPy), `faixa`
  (`{"de":"pi/3","ate":"2*pi/3"}` — setor sombreado, a região-solução), `linha_valor`
  (`{"y":"sqrt(3)/2","rotulo":"..."}` — reta horizontal de referência, pra "sen(x) >
  valor").
- `"acao": "plano_complexo"` — plano de Argand-Gauss, pra números complexos, raízes
  da unidade, rotação por multiplicação. Campos: `pontos` (`{"re":2,"im":0,
  "rotulo":"2"}`), `vetores` (True desenha seta em vez de bolinha), `poligono` (True
  conecta os pontos em ordem — ex. raízes formando um polígono), `raio_circulo`
  (desenha uma circunferência de referência), `dominio`/`imagem` como em `grafico`.
- `"acao": "vetores_2d"` — vetores no plano, soma pela regra do paralelogramo, pra
  geometria analítica vetorial (produto escalar, projeção, área). Campos: `vetores`
  (até 3, `{"x":3,"y":4,"rotulo":"u"}`, saem da origem), `somar` (True, só com
  exatamente 2 vetores, desenha a soma e o paralelogramo tracejado), `rotulo_soma`.
- `"acao": "grade_polar"` — grade de coordenadas polares, pra radar/distância entre
  pontos polares, ângulo central (lei dos cossenos). Campos: `raio_max`, `pontos`
  (`{"r":6,"theta":"pi/6","rotulo":"A"}`, `theta` em radianos), `segmento` (True liga
  dois pontos, pra mostrar a distância entre eles).
- `"acao": "tabela_dados"` — tabela de linhas/colunas, pra estatística (distribuição
  de frequência, médias) ou qualquer contagem organizada em tabela. Campos:
  `cabecalho` (lista de títulos de coluna), `linhas` (lista de listas, mesma
  quantidade de colunas do cabeçalho), `destacar_coluna` (índice 0-based pra
  destacar em dourado — ex. a coluna recém-calculada).
- `"acao": "esboco"` — canvas livre com 6 primitivas simples (`ponto`, `segmento`,
  `seta`, `circulo`, `retangulo`, `texto`), cor sempre por nome da paleta
  (`"giz"|"destaque"|"apoio"|"nota"`, nunca hex). É a válvula de escape pra quando a
  questão pede algo que nenhum dos outros 12 cobre — diagrama de Venn, urna, esquema
  de fluxo curto. Máximo de ~10-14 elementos.
- `"acao": "solido_3d"` — cone, cilindro ou esfera em perspectiva 3D de verdade (a
  câmera inclina só pra esse passo e volta pra visão plana logo depois — automático,
  não precisa de nada especial no resto do roteiro). Campos: `tipo` (`"cone"` |
  `"cilindro"` | `"esfera"`), `raio`, `altura` (ignorada em esfera), `corte_altura`
  (altura medida da base de uma secção transversal — só cone/cilindro, o raio da
  secção em cone é calculado por semelhança de triângulos automaticamente),
  `rotular_raio`/`rotular_altura` (texto opcional). **Não aceita `fixar`** — depois
  do sólido a câmera volta a plana, então não faz sentido deixá-lo "grudado" no
  canto. Categoria mais recente e mais arriscada visualmente das 12: prefira sempre
  o menor número de rótulos/elementos, e não empilhe dois `solido_3d` muito perto um
  do outro no mesmo roteiro.

Todos os outros 11 aceitam `fixar: true` igual à `figura` — encolhe e ancora no canto superior
direito, ficando visível enquanto o resto da resolução é escrito ao lado.

**Use os parâmetros com criatividade, mas sem extravagância.** Os 12 primeiros tipos
têm forma fixa (é assim que se evita um SVG livre saindo torto); dentro deles, os
números/textos/quantidade de pontos são livres. `esboco` dá mais liberdade de
composição ainda, mas continua sendo só 6 primitivas simples, sempre na paleta
do projeto — nunca desenhe fora dessas 6 primitivas, e nunca em hexadecimal cru. Regra
prática: se está em dúvida se um diagrama "ficaria estranho", é sinal de que ficaria —
prefira algo mais simples (menos elementos, menos texto dentro do desenho) a arriscar.
Metas de HARMONIA e POSICIONAMENTO, sempre:
  - Poucos elementos por diagrama (2-3 funções, 3-5 vértices, árvore com 2-3 níveis,
    grade/tabuleiro até uns 6×6-8, esboço com ~6-10 elementos, poucos ângulos no
    ciclo trigonométrico, até 3 vetores, poucos pontos na grade polar, tabela com
    até uns 5-6 linhas) — o objetivo é clareza tipo quadro-negro, não infográfico
    carregado.
  - Deixe folga: nada deve encostar na borda do quadro nem em outro elemento. Se um
    rótulo for colidir com outra coisa (outro texto, uma seta, o próprio desenho),
    prefira encurtar o texto ou espaçar mais os pontos a deixar sobrepor.
  - Proporção: escolha domínio/imagem/coordenadas que deixem a figura mais ou menos
    equilibrada (nem esticada, nem espremida) — evite por exemplo x de -50 a 50 com y
    de -1 a 1 só porque os números da questão são grandes; normalize/rotule os eixos
    em vez de forçar uma escala desproporcional.
  - Depois de montar um roteiro com diagrama, releia os parâmetros como se estivesse
    imaginando o resultado: os pontos citados fazem um desenho coerente com o
    enunciado? Nada em cima de nada?

### Animações (avançado, opcional — use com moderação)

Além dos diagramas estáticos, `quadro.py` tem 3 templates de animação **aprovados**
pra ilustrar um PROCESSO em vez de um estado parado — mais próximo do estilo
3Blue1Brown de verdade. São máquinas de estado curtas e determinísticas (2-4
transições), não simulação livre:

- `"acao": "anim_pg_infinita"` — retângulo se enchendo fatia a fatia, mostra que a
  soma de uma PG infinita converge pra área total. Campos: `primeiro_termo` (fração
  0-1 da largura), `razao` (0-1), `max_iteracoes` (padrão 6). Pra PG infinita, fração
  geratriz, paradoxo de convergência.
- `"acao": "anim_riemann"` — retângulos de Riemann se refinando (4→8→16→32) até
  colar na curva. Campos: `expr` (função positiva no domínio), `dominio` `[a,b]`,
  `iteracoes` (padrão `[4,8,16,32]`). Pra área sob o gráfico, introdução à integral.
- `"acao": "anim_seno"` — ponto girando no ciclo trigonométrico "desenrolando" a
  senoide ao lado, em tempo real. Campos: `funcao` (`"seno"`|`"cosseno"`),
  `frequencia` (mostra compressão de período de sen(kx)), `voltas`. Pra
  periodicidade, imagem de função trigonométrica.

Existem outros 3 templates no código (`anim_discriminante`, `anim_peneira`,
`anim_corrida`) que **funcionam mas ainda não foram aprovados visualmente** — não
os use por padrão numa resolução real a menos que o usuário peça explicitamente ou
confirme que quer testá-los de novo.

Todos aceitam `fixar: true` como os diagramas estáticos. Use animação só quando o
PROCESSO (convergindo, se refinando, girando) for o ponto pedagógico da questão —
pra tudo que é só "mostrar uma figura parada", os diagramas estáticos continuam
sendo a escolha certa (mais rápidos de renderizar, menos risco visual).

## Passo 2 — Validar (trava obrigatória)

```
conda run -n no_alvo python motor/validar.py roteiros/<id>.json
```

- `REPROVADO` → **não siga adiante**. Corrija o roteiro (a modelagem, a fórmula, ou o
  `alternativa_calculada`) e rode de novo até `APROVADO`.
- Avisos de SymPy ("não verificado automaticamente") não bloqueiam, mas confira a
  conta à mão antes de prosseguir se o `tipo` de validação não cobriu o cálculo.

## Passo 3 — Gerar áudio (Coqui XTTS-v2)

```
conda run -n no_alvo python tts/xtts_audio.py roteiros/<id>.json
```

Isso baixa o modelo XTTS-v2 na primeira execução (~2GB, fica em cache depois) e gera
`tts/audio/<id>/passo_NN.wav` + `manifesto.json` com a duração real de cada fala. Voz
padrão é "Luis Moray" (`XTTS_SPEAKER` — venceu uma comparação de vozes prontas do
XTTS, ver `tts/amostras_vozes/`); só troque se o usuário pedir outra voz ou clonagem
(`XTTS_SPEAKER_WAV`). Velocidade (`XTTS_SPEED`, padrão 1.1) e temperatura
(`XTTS_TEMPERATURE`, padrão 0.5 — baixa de propósito, prioriza estabilidade sobre
expressividade pra vídeo de aula) também são ajustáveis por variável de ambiente. A
síntese já quebra frases longas em cláusulas e nunca manda pontuação pro modelo (ver
docstring de `tts/xtts_audio.py`) — não precisa se preocupar com isso ao escrever
`narracao`, só evitar `:`/`;`/`a)` como já dito no Passo 1. Ela também nunca isola
um fragmento curto sozinho (`LIMITE_FRAGMENTO_MIN`) — evita o corte brusco que
acontecia em coordenadas/combinações tipo "n menos um" sozinho depois de uma
vírgula de notação (não de pausa de prosa). Ainda assim, ao narrar um par
coordenado ou uma combinação, prefira "e" a vírgula quando der ("n menos um e n
mais um" em vez de "n menos um, n mais um") — funciona melhor que depender só do
código.

## Passo 4 — Renderizar o vídeo

```
cd motor
ROTEIRO=$(pwd)/../roteiros/<id>.json AUDIO_DIR=$(pwd)/../tts/audio/<id> \
  conda run -n no_alvo manim -qh --fps 30 --disable_caching -o <id> render.py Aula
```

`-qh` dá a resolução 1920x1080, mas o padrão dela vem em 60fps — `--fps 30` sobrescreve
só o frame rate (renderiza mais rápido, sem perda perceptível: é um quadro didático
estático, não tem movimento rápido que precise de 60fps). É o padrão pra entrega
final. Use `-ql` (480p15, bem mais rápido) só pra teste rápido de layout enquanto
ainda está ajustando o roteiro.

Com `AUDIO_DIR` presente, cada cena dura o tempo real da fala e o áudio já entra
sincronizado — não precisa fazer nada além disso. O vídeo final fica em
`motor/media/videos/render/<qualidade>/<id>.mp4`; informe o caminho ao usuário ao
terminar. `render.py` também escreve `roteiros/<id>.narracao.txt` com o texto lido,
útil para conferência.

Para gerar vários de uma vez, use `motor/lote.sh <id1> <id2> ...` (mesmo pipeline dos
passos 3-4, roteiro por roteiro).

### Atalho: pipeline completo com um comando

`motor/gerar_final.sh <id>` faz os passos 2-4 inteiros (valida → áudio → renderiza
1080p/30fps → junta vinheta no início e no fim) de uma vez só:

```
bash motor/gerar_final.sh catalan-caminhos-n4
```

Sai em `motor/media/videos/render/1080p30/<id>-COMPLETO.mp4`. Precisa de
`vinheta/vinheta_inicio.mp4` e `vinheta/vinheta_fim.mp4` (vídeo de abertura/
encerramento do "No Alvo" com uma musiquinha leve — crescendo no início,
descendo no fim; sem eles o script avisa e sai só o vídeo sem vinheta).

## Regras que não podem quebrar

- Nunca renderize um roteiro que não passou pela validação (passo 2).
- Nunca escreva fórmula/LaTeX dentro de um campo `narracao` — é a garantia de que o
  TTS não tenta "ler" símbolos matemáticos.
- Cores e layout do quadro são fixos em `motor/quadro.py` (paleta "No Alvo": preto +
  dourado + branco) — não hardcode cor nenhuma dentro de um roteiro JSON.
- `motor/render.py` é genérico e não conhece questão nenhuma; toda diferença entre
  questões vem só do JSON. Se algo parecer exigir mexer em `render.py` ou
  `quadro.py` por causa de uma questão específica, pare e repense o roteiro antes.
