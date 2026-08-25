#!/bin/bash
# Pipeline completo de um roteiro até o vídeo final com vinheta.
#
# Faz, em ordem: valida (gabarito+SymPy) -> gera áudio (XTTS-v2) -> renderiza
# (Manim, 1080p/30fps) -> junta vinheta no início e no fim. Para na hora se
# algum passo falhar (set -e) — não adianta gerar áudio de roteiro reprovado.
#
# Uso:  bash gerar_final.sh <id>
#   <id> = nome do roteiro em roteiros/<id>.json (sem a extensão)
#
# Ajuste fino do áudio (vozes, velocidade, temperatura etc.) fica em
# tts/xtts_audio.py — rode só esse script de novo se só o áudio precisar
# regenerar (sem precisar re-renderizar o resto, a menos que o áudio mude
# de duração).
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ID="$1"

if [ -z "$ID" ]; then
  echo "Uso: bash gerar_final.sh <id>   (roteiro em roteiros/<id>.json)"
  exit 1
fi

ROTEIRO="$DIR/../roteiros/$ID.json"
AUDIO_DIR="$DIR/../tts/audio/$ID"
VINHETA_DIR="$DIR/../vinheta"
SAIDA_DIR="$DIR/media/videos/render/1080p30"

if [ ! -f "$ROTEIRO" ]; then
  echo "Não encontrei $ROTEIRO"
  exit 1
fi

echo "== 1/4 validando (gabarito + SymPy) =="
conda run -n no_alvo python "$DIR/validar.py" "$ROTEIRO"

echo "== 2/4 gerando áudio (Coqui XTTS-v2) =="
conda run -n no_alvo python "$DIR/../tts/xtts_audio.py" "$ROTEIRO"

echo "== 3/4 renderizando (1080p, 30fps) =="
cd "$DIR"
ROTEIRO="$ROTEIRO" AUDIO_DIR="$AUDIO_DIR" \
  conda run -n no_alvo manim -qh --fps 30 --disable_caching -o "$ID" render.py Aula

echo "== 4/4 juntando vinheta (início + fim) =="
if [ ! -f "$VINHETA_DIR/vinheta_inicio.mp4" ] || [ ! -f "$VINHETA_DIR/vinheta_fim.mp4" ]; then
  echo "AVISO: vinheta_inicio.mp4/vinheta_fim.mp4 não encontrados em $VINHETA_DIR"
  echo "       o vídeo final ficou sem vinheta: $SAIDA_DIR/$ID.mp4"
  exit 0
fi

FINAL="$SAIDA_DIR/${ID}-COMPLETO.mp4"
ffmpeg -y -v error \
  -i "$VINHETA_DIR/vinheta_inicio.mp4" -i "$SAIDA_DIR/$ID.mp4" -i "$VINHETA_DIR/vinheta_fim.mp4" \
  -filter_complex "[0:v]scale=1920:1080,setsar=1,fps=30[v0];[1:v]scale=1920:1080,setsar=1,fps=30[v1];[2:v]scale=1920:1080,setsar=1,fps=30[v2];[v0][0:a][v1][1:a][v2][2:a]concat=n=3:v=1:a=1[v][a]" \
  -map "[v]" -map "[a]" -c:v libx264 -pix_fmt yuv420p -c:a aac -b:a 192k "$FINAL"

echo
echo "Pronto: $FINAL"
