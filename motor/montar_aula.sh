#!/bin/bash
# Monta uma AULA longa a partir de vários capítulos (roteiros independentes).
#
# É o mesmo padrão do vídeo de recorrência: cada capítulo é um roteiro próprio em
# roteiros/<id>.json, renderizado sozinho, e no fim tudo é concatenado numa peça só
# com a vinheta de abertura e de encerramento.
#
# Uso:  bash montar_aula.sh <nome-da-aula> <id1> <id2> ...
#   ex: bash montar_aula.sh equilibrio equilibrio-01-intro equilibrio-02-kc ...
#
# Para cada <id> roda o gerar_final.sh SEM vinheta (valida -> áudio -> render) e
# depois cola tudo. Se um capítulo já estiver renderizado, ele é reaproveitado.
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AULA="$1"; shift
IDS=("$@")

if [ -z "$AULA" ] || [ ${#IDS[@]} -eq 0 ]; then
  echo "Uso: bash montar_aula.sh <nome-da-aula> <id1> <id2> ..."
  exit 1
fi

SAIDA_DIR="$DIR/media/videos/render/1080p30"
VINHETA_DIR="$DIR/../vinheta"
LISTA="$(mktemp)"

for ID in "${IDS[@]}"; do
  MP4="$SAIDA_DIR/$ID.mp4"
  if [ ! -f "$MP4" ]; then
    echo "== capítulo $ID (validando, gerando áudio e renderizando) =="
    conda run -n no_alvo python "$DIR/validar.py" "$DIR/../roteiros/$ID.json"
    conda run -n no_alvo python "$DIR/../tts/xtts_audio.py" "$DIR/../roteiros/$ID.json"
    ( cd "$DIR" && ROTEIRO="$DIR/../roteiros/$ID.json" AUDIO_DIR="$DIR/../tts/audio/$ID" \
        conda run -n no_alvo manim -qh --fps 30 -o "$ID" render.py Aula )
  else
    echo "== capítulo $ID já renderizado, reaproveitando =="
  fi
done

# ordem final: vinheta de abertura, capítulos, vinheta de encerramento
ARQS=()
[ -f "$VINHETA_DIR/vinheta_inicio.mp4" ] && ARQS+=("$VINHETA_DIR/vinheta_inicio.mp4")
for ID in "${IDS[@]}"; do ARQS+=("$SAIDA_DIR/$ID.mp4"); done
[ -f "$VINHETA_DIR/vinheta_fim.mp4" ] && ARQS+=("$VINHETA_DIR/vinheta_fim.mp4")

# normaliza tudo para 1920x1080/30fps antes de concatenar: capítulos renderizados em
# qualidades diferentes (ou a vinheta em outro tamanho) quebrariam o concat puro.
ENTRADAS=(); FILTRO=""; N=${#ARQS[@]}
for i in "${!ARQS[@]}"; do
  ENTRADAS+=(-i "${ARQS[$i]}")
  FILTRO+="[$i:v]scale=1920:1080,setsar=1,fps=30[v$i];"
done
for i in "${!ARQS[@]}"; do FILTRO+="[v$i][$i:a]"; done
FILTRO+="concat=n=$N:v=1:a=1[v][a]"

FINAL="$SAIDA_DIR/${AULA}-COMPLETO.mp4"
echo "== colando $N trechos em $FINAL =="
ffmpeg -y -v error "${ENTRADAS[@]}" -filter_complex "$FILTRO" \
  -map "[v]" -map "[a]" -c:v libx264 -pix_fmt yuv420p -c:a aac -b:a 192k "$FINAL"

rm -f "$LISTA"
echo
echo "Pronto: $FINAL"
