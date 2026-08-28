# Pipeline de vídeo-aula — resolução animada de questões

Pipeline que transforma a foto (ou PDF/texto/LaTeX) de uma questão num vídeo de
resolução: quadro didático animado em Manim, em paleta preto + dourado +
branco, com narração gerada localmente
por TTS (Coqui XTTS-v2) — sem depender de nenhuma API paga. Além de escrever
fórmulas, o motor sabe desenhar 13 tipos de diagrama (gráfico, geometria,
círculo trigonométrico, plano complexo, vetores, sólidos 3D, etc.) e 3
templates de animação (soma de PG infinita, somas de Riemann, ciclo
trigonométrico ↔ senoide) — ver a lista completa em
`.claude/skills/resolver-questao/SKILL.md`.

O fluxo completo (foto → roteiro → validação → áudio → vídeo) está descrito
passo a passo em `.claude/skills/resolver-questao/SKILL.md`; é a esse arquivo
que o Claude Code recorre quando você pede pra resolver uma questão. Este
README cobre só a instalação e a estrutura do projeto.

> **Nota:** mídia gerada pelo pipeline (vídeos renderizados, áudio) e pastas
> de teste/experimento não são versionadas neste repositório — ver
> `.gitignore`. Os assets de vinheta (`vinheta_inicio.mp4`, `vinheta_fim.mp4`,
> músicas de abertura/encerramento) também ficam de fora por serem binários
> grandes; substitua pelos seus próprios antes de rodar `gerar_final.sh`, ou
> peça os originais separadamente.

## Estrutura

```
motor/            quadro.py (layout/paleta/diagramas/animações), render.py (lê
                   roteiro JSON e desenha), validar.py (trava de gabarito +
                   SymPy), lote.sh (renderiza vários roteiros de uma vez),
                   gerar_final.sh (pipeline completo: valida→áudio→renderiza→
                   junta vinheta, um comando só — ver "Uso rápido" abaixo)
tts/               xtts_audio.py (TTS local, Coqui XTTS-v2);
                   amostras_vozes/ (comparação de vozes prontas do XTTS)
roteiros/          roteiros JSON prontos (um por questão)
fotos/             fotos de questões a resolver (não versionado)
roteiro_exemplo.json   roteiro de referência — schema completo comentado
requirements.txt   dependências pip (ver setup.sh/setup.ps1 abaixo)
```

### Uso rápido (depois de instalado)

```
bash motor/gerar_final.sh <id>
```

Faz tudo: valida `roteiros/<id>.json`, gera o áudio, renderiza em 1080p/30fps e
junta a vinheta no início e no fim. Sai em
`motor/media/videos/render/1080p30/<id>-COMPLETO.mp4`. Pra rodar só uma etapa
(ex.: só regenerar áudio depois de mudar `narracao`), use os comandos
individuais da seção "Testar" abaixo ou do `SKILL.md`.

O renderizador (`motor/render.py`) usa `ThreeDScene` do Manim (não `Scene`) pra
suportar o diagrama `solido_3d` — vídeos sem nenhum passo 3D renderizam
idêntico a antes, só um pouco mais devagar (a câmera 3D-capable tem mais
overhead mesmo parada).

## Instalação

Precisa de **conda** (Miniconda/Anaconda), **ffmpeg** e uma distribuição
**LaTeX** instalados no sistema — os scripts abaixo checam e avisam se
faltar alguma, mas não instalam esses três sozinhos.

**Linux / macOS:**
```
bash setup.sh
```

**Windows** (no Anaconda PowerShell Prompt):
```
powershell -ExecutionPolicy Bypass -File setup.ps1
```

O script cria o ambiente conda `no_alvo` (Python 3.12), instala as
dependências de sistema do Manim (pango/cairo/harfbuzz, via conda-forge —
evita compilar nada na mão) e instala o PyTorch **detectando sozinho** se dá
pra usar GPU:

- **GPU NVIDIA detectada** → instala PyTorch com CUDA e testa rodar um tensor
  nela; se a placa for antiga demais pro build (ex.: compute capability
  baixa), cai pra CPU automaticamente.
- **macOS** → instala o PyTorch padrão, que usa aceleração Metal/MPS quando
  disponível.
- **Sem GPU NVIDIA** → instala PyTorch CPU-only. Mais lento pra gerar áudio,
  mas funciona igual — é processamento em lote, não precisa ser tempo real.

Rode de novo sempre que quiser (é idempotente).

### Instalação manual (sem os scripts)

```
conda create -n no_alvo -c conda-forge --override-channels python=3.12
conda install -n no_alvo -c conda-forge --override-channels \
  pango cairo pkg-config gobject-introspection harfbuzz zlib expat glib fribidi

# escolha UMA linha, conforme sua GPU:
conda run -n no_alvo pip install torch==2.8.0 torchaudio==2.8.0 \
  --index-url https://download.pytorch.org/whl/cpu      # sem GPU NVIDIA
conda run -n no_alvo pip install torch==2.8.0 torchaudio==2.8.0 \
  --index-url https://download.pytorch.org/whl/cu126     # com GPU NVIDIA
conda run -n no_alvo pip install torch==2.8.0 torchaudio==2.8.0  # macOS

conda run -n no_alvo pip install -r requirements.txt
```

## Testar

Renderização sem áudio (rápido, confirma que o Manim/LaTeX estão ok):
```
cd motor
ROTEIRO=../roteiro_exemplo.json conda run -n no_alvo manim -ql --disable_caching -o teste render.py Aula
```

Pipeline completo com áudio:
```
conda run -n no_alvo python tts/xtts_audio.py roteiro_exemplo.json
cd motor
ROTEIRO=../roteiro_exemplo.json AUDIO_DIR=../tts/audio/afa-2018-q19 \
  conda run -n no_alvo manim -qh --fps 30 --disable_caching -o teste render.py Aula
```
(`-qh` = 1080p, o padrão pra entrega final; `--fps 30` sobrescreve o 60fps padrão
da `-qh` — sem perda perceptível pra quadro didático estático. `-ql` = 480p15,
bem mais rápido, pra teste rápido de layout.)

O vídeo sai em `motor/media/videos/render/<qualidade>/teste.mp4`.

## Notas / pegadinhas conhecidas

- **Primeira execução do XTTS-v2** baixa o modelo (~2GB) — só acontece uma
  vez, fica em cache depois (`~/.local/share/tts`).
- **Licença do modelo XTTS-v2**: CPML (Coqui Public Model License) — uso
  não-comercial livre; uso comercial exige licença da Coqui
  (https://coqui.ai/cpml). Confira antes de monetizar vídeos com essa voz.
- **`transformers` é fixado em 4.57.6** no `requirements.txt` — versões 5.x
  quebram o coqui-tts (função interna renomeada). Se algum dia atualizar o
  coqui-tts e a instalação falhar com erro de `isin_mps_friendly`, é isso.
- **torch é pinado em 2.8.0** de propósito: a partir do 2.9 o torch passa a
  exigir a lib `torchcodec` pra I/O de áudio, e o pacote `torchcodec` do PyPI
  vem compilado pra CUDA — quebra em máquina sem GPU NVIDIA mesmo rodando
  tudo em CPU. Fique nessa versão até resolver isso de verdade se for
  atualizar o torch.
- **Voz do XTTS**: usa uma voz pronta da biblioteca por padrão (hoje "Luis
  Moray", variável `XTTS_SPEAKER` em `tts/xtts_audio.py` — ver comparação em
  `tts/amostras_vozes/`); dá pra trocar por clonagem de voz com
  `XTTS_SPEAKER_WAV` apontando pra uma amostra de 10-30s. `XTTS_SPEED` (padrão
  1.1) e `XTTS_TEMPERATURE` (padrão 0.5, baixo de propósito pra priorizar
  estabilidade sobre expressividade) também são ajustáveis.
- **Pontuação e XTTS-v2**: o modelo às vezes lê sinais de pontuação em voz
  alta em português (":" vira "dois pontos" falado). `tts/xtts_audio.py` já
  contorna isso quebrando o texto em frases/cláusulas antes de sintetizar, sem
  mandar pontuação nenhuma pro modelo — não precisa se preocupar com isso ao
  escrever roteiros nem mexer nesse script.
- **Animações são mais caras que diagramas estáticos**: usam `ValueTracker` +
  `always_redraw` (recalcula a cada frame) ou `get_riemann_rectangles`, então
  renderizam mais devagar que os diagramas parados. Use com moderação — só
  quando o ponto pedagógico for realmente um PROCESSO, não um estado fixo.
