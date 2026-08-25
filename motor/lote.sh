#!/bin/bash
# Renderiza em lote os roteiros listados. Caminhos relativos a este arquivo, então
# funciona em qualquer clone do projeto — não depende de onde o repo foi checado out.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
for r in "$@"; do
  ROTEIRO="$DIR/../roteiros/$r.json" AUDIO_DIR="$DIR/../tts/audio/$r" \
    conda run -n no_alvo manim -qh --fps 30 --disable_caching -o "$r" render.py Aula \
    2>&1 | grep -iE "rendered|error" | tail -1
  echo "FEITO $r"
done
echo LOTE_COMPLETO
