#!/bin/bash
# Pipeline pra vídeo temático/compilado (várias seções, cada uma seu próprio
# roteiro JSON) — diferente do gerar_final.sh, que é pra UMA questão só.
#
# Cada seção é gerada e renderizada de forma INCREMENTAL: se o .mp4 da seção
# já existe e é mais novo que o roteiro JSON dela, pula (não perde tempo
# re-processando o que não mudou). Só regenera o que precisa.
#
# Roteiros de seção não têm gabarito/alternativas (não são questão de múltipla
# escolha) — por isso a validação de gabarito do validar.py é pulada aqui.
#
# Uso:  bash gerar_compilado.sh <id-do-video> <secao1> <secao2> ... <secaoN>
# Ex.:  bash gerar_compilado.sh recorrencia recorrencia-01-intro \
#         recorrencia-02-fibonacci recorrencia-03-domino \
#         recorrencia-04-hanoi recorrencia-05-moser recorrencia-06-conclusao
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VIDEO_ID="$1"
shift
SECOES=("$@")

if [ -z "$VIDEO_ID" ] || [ "${#SECOES[@]}" -eq 0 ]; then
  echo "Uso: bash gerar_compilado.sh <id-do-video> <secao1> <secao2> ..."
  exit 1
fi

SAIDA_DIR="$DIR/media/videos/render/1080p30"
VINHETA_DIR="$DIR/../vinheta"
mkdir -p "$SAIDA_DIR"

for SEC in "${SECOES[@]}"; do
  ROTEIRO="$DIR/../roteiros/$SEC.json"
  AUDIO_DIR="$DIR/../tts/audio/$SEC"
  VIDEO_SECAO="$SAIDA_DIR/$SEC.mp4"

  if [ ! -f "$ROTEIRO" ]; then
    echo "ERRO: não encontrei $ROTEIRO"
    exit 1
  fi

  if [ -f "$VIDEO_SECAO" ] && [ "$VIDEO_SECAO" -nt "$ROTEIRO" ]; then
    echo "== $SEC: já renderizado e mais novo que o roteiro, pulando =="
    continue
  fi

  echo "== $SEC: 1/2 gerando áudio =="
  conda run -n no_alvo python "$DIR/../tts/xtts_audio.py" "$ROTEIRO"

  echo "== $SEC: 2/2 renderizando (1080p, 30fps) =="
  cd "$DIR"
  ROTEIRO="$ROTEIRO" AUDIO_DIR="$AUDIO_DIR" \
    conda run -n no_alvo manim -qh --fps 30 --disable_caching -o "$SEC" render.py Aula
done

# Cada clipe funde pro preto/silêncio na entrada e na saída (fade curto,
# dentro da própria duração dele — não sobrepõe com o clipe vizinho) e depois
# tudo é concatenado sem cortar nem sobrepor tempo nenhum. Testamos crossfade
# (xfade/acrossfade) antes, mas misturar a voz do fim de uma seção com o
# início da narração seguinte soa como um "travamento" (duas falas por cima
# uma da outra) — em vez disso, cada seção baixa pro silêncio, corta, e a
# próxima já entra subindo de novo; mais parecido com um corte de vídeo
# profissional que com uma dissolução, e sem risco de desalinhar áudio/vídeo
# (aqui a duração de saída é exatamente a soma das durações de entrada, sem
# nenhuma conta de offset acumulado que possa desalinhar as duas trilhas).
FADE="${FADE_S:-0.35}"

echo "== juntando vinheta + ${#SECOES[@]} seções + vinheta (fade de ${FADE}s por corte) =="
ARQUIVOS=("$VINHETA_DIR/vinheta_inicio.mp4")
for SEC in "${SECOES[@]}"; do
  ARQUIVOS+=("$SAIDA_DIR/$SEC.mp4")
done
ARQUIVOS+=("$VINHETA_DIR/vinheta_fim.mp4")

N_TOTAL=${#ARQUIVOS[@]}
INPUTS=()
for F in "${ARQUIVOS[@]}"; do
  INPUTS+=(-i "$F")
done

DURACOES=()
for F in "${ARQUIVOS[@]}"; do
  DURACOES+=("$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$F")")
done

FILTER=""
CONCAT_REFS=""
for ((i = 0; i < N_TOTAL; i++)); do
  SAIDA_EM=$(awk -v d="${DURACOES[$i]}" -v f="$FADE" 'BEGIN{printf "%.3f", d - f}')
  FILTER+="[$i:v]scale=1920:1080,setsar=1,fps=30,fade=t=in:st=0:d=${FADE},fade=t=out:st=${SAIDA_EM}:d=${FADE}[v$i];"
  FILTER+="[$i:a]afade=t=in:st=0:d=${FADE},afade=t=out:st=${SAIDA_EM}:d=${FADE}[a$i];"
  CONCAT_REFS+="[v$i][a$i]"
done
FILTER+="${CONCAT_REFS}concat=n=${N_TOTAL}:v=1:a=1[v][a]"

FINAL="$SAIDA_DIR/${VIDEO_ID}-COMPLETO.mp4"
ffmpeg -y -v error "${INPUTS[@]}" -filter_complex "$FILTER" \
  -map "[v]" -map "[a]" -c:v libx264 -pix_fmt yuv420p -c:a aac -b:a 192k "$FINAL"

echo
echo "Pronto: $FINAL"
