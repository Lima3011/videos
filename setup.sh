#!/usr/bin/env bash
# Configura o ambiente do projeto "No Alvo" — Linux e macOS.
#
# Cria o env conda "no_alvo" com tudo que o motor precisa (Manim + Coqui XTTS-v2),
# detectando automaticamente se a máquina tem GPU NVIDIA utilizável — senão cai
# pra CPU sozinho. Idempotente: rodar de novo não duplica nada.
#
# Uso:  bash setup.sh
set -e

ENV_NAME=no_alvo
PY_VER=3.12
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

command -v conda >/dev/null 2>&1 || {
  echo "conda não encontrado. Instale o Miniconda primeiro:"
  echo "  https://docs.conda.io/en/latest/miniconda.html"
  exit 1
}
source "$(conda info --base)/etc/profile.d/conda.sh"

echo "== verificando ffmpeg/LaTeX (o script não instala isso automaticamente) =="
command -v ffmpeg >/dev/null 2>&1 || echo "AVISO: ffmpeg não encontrado no PATH.
  Linux:  sudo apt install ffmpeg   (ou dnf/pacman equivalente)
  macOS:  brew install ffmpeg"
command -v latex >/dev/null 2>&1 || echo "AVISO: LaTeX não encontrado no PATH (necessário pro MathTex do Manim).
  Linux:  sudo apt install texlive texlive-latex-extra
  macOS:  brew install --cask basictex   (depois: sudo tlmgr update --self && sudo tlmgr install standalone preview)"

echo "== criando ambiente conda '$ENV_NAME' (python $PY_VER) =="
conda env list | grep -q "^$ENV_NAME " || \
  conda create -y -n "$ENV_NAME" -c conda-forge --override-channels "python=$PY_VER"

echo "== dependências de sistema do Manim (pango/cairo/harfbuzz), via conda-forge =="
# manimpango (usado pelo Manim pra texto) compila do zero se essas libs de
# desenvolvimento não existirem — instalar antes do pip evita esse build.
conda install -y -n "$ENV_NAME" -c conda-forge --override-channels \
  pango cairo pkg-config gobject-introspection harfbuzz zlib expat glib fribidi

install_cpu_torch() {
  echo "Instalando PyTorch (CPU)."
  conda run -n "$ENV_NAME" pip install torch==2.8.0 torchaudio==2.8.0 \
    --index-url https://download.pytorch.org/whl/cpu
}

echo "== PyTorch =="
OS="$(uname -s)"
if command -v nvidia-smi >/dev/null 2>&1; then
  echo "GPU NVIDIA detectada — instalando PyTorch com CUDA."
  conda run -n "$ENV_NAME" pip install torch==2.8.0 torchaudio==2.8.0 \
    --index-url https://download.pytorch.org/whl/cu121
  echo "Conferindo se a GPU realmente roda com esse build (placas antigas às vezes não têm os kernels)..."
  if ! conda run -n "$ENV_NAME" python -c "
import torch
assert torch.cuda.is_available()
torch.zeros(1).cuda() + 1
" >/dev/null 2>&1; then
    echo "GPU detectada, mas incompatível com este build de PyTorch — caindo pra CPU (mais lento, porém confiável)."
    conda run -n "$ENV_NAME" pip uninstall -y torch torchaudio >/dev/null 2>&1 || true
    install_cpu_torch
  fi
elif [ "$OS" = "Darwin" ]; then
  echo "macOS — instalando PyTorch padrão (usa aceleração Metal/MPS quando disponível, sem CUDA)."
  conda run -n "$ENV_NAME" pip install torch==2.8.0 torchaudio==2.8.0
else
  echo "Sem GPU NVIDIA detectada."
  install_cpu_torch
fi

echo "== manim, sympy, coqui-tts =="
conda run -n "$ENV_NAME" pip install -r "$DIR/requirements.txt"

echo
echo "Pronto. Para usar:"
echo "  conda activate $ENV_NAME"
echo "Pra testar a renderização (sem áudio, rápido):"
echo "  cd $DIR/motor && ROTEIRO=$DIR/roteiro_exemplo.json conda run -n $ENV_NAME manim -ql --disable_caching -o teste render.py Aula"
echo "Veja README.md para o passo a passo completo."
