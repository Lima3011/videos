# Configura o ambiente do projeto "No Alvo" — Windows (PowerShell).
#
# Cria o env conda "no_alvo" com tudo que o motor precisa (Manim + Coqui XTTS-v2),
# detectando automaticamente se a máquina tem GPU NVIDIA utilizável — senão cai
# pra CPU sozinha. Idempotente: rodar de novo não duplica nada.
#
# Uso (no Anaconda PowerShell Prompt):
#   powershell -ExecutionPolicy Bypass -File setup.ps1

$ErrorActionPreference = "Stop"
$EnvName = "no_alvo"
$PyVer = "3.12"
$Dir = $PSScriptRoot

if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
    Write-Host "conda não encontrado. Instale o Miniconda primeiro:"
    Write-Host "  https://docs.conda.io/en/latest/miniconda.html"
    exit 1
}

Write-Host "== verificando ffmpeg/LaTeX (o script não instala isso automaticamente) =="
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "AVISO: ffmpeg não encontrado no PATH."
    Write-Host "  choco install ffmpeg   (ou baixe em https://ffmpeg.org/download.html)"
}
if (-not (Get-Command latex -ErrorAction SilentlyContinue)) {
    Write-Host "AVISO: LaTeX não encontrado no PATH (necessário pro MathTex do Manim)."
    Write-Host "  Instale o MiKTeX: https://miktex.org/download"
}

Write-Host "== criando ambiente conda '$EnvName' (python $PyVer) =="
$envs = conda env list
if ($envs -notmatch "^\s*$EnvName\s") {
    conda create -y -n $EnvName -c conda-forge --override-channels "python=$PyVer"
}

Write-Host "== dependências de sistema do Manim (pango/cairo/harfbuzz), via conda-forge =="
# manimpango (usado pelo Manim pra texto) compila do zero se essas libs de
# desenvolvimento não existirem — instalar antes do pip evita esse build.
conda install -y -n $EnvName -c conda-forge --override-channels `
    pango cairo pkg-config gobject-introspection harfbuzz zlib expat glib fribidi

function Install-CpuTorch {
    Write-Host "Instalando PyTorch (CPU)."
    conda run -n $EnvName pip install torch==2.8.0 torchaudio==2.8.0 `
        --index-url https://download.pytorch.org/whl/cpu
}

Write-Host "== PyTorch =="
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    Write-Host "GPU NVIDIA detectada — instalando PyTorch com CUDA."
    # cu121 parou em torch 2.5.1 (índice não é mais atualizado); cu126 é o
    # primeiro índice CUDA que ainda publica exatamente o torch 2.8.0 pinado
    conda run -n $EnvName pip install torch==2.8.0 torchaudio==2.8.0 `
        --index-url https://download.pytorch.org/whl/cu126

    Write-Host "Conferindo se a GPU realmente roda com esse build (placas antigas às vezes não têm os kernels)..."
    conda run -n $EnvName python -c "import torch; assert torch.cuda.is_available(); torch.zeros(1).cuda() + 1" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "GPU detectada, mas incompatível com este build de PyTorch — caindo pra CPU (mais lento, porém confiável)."
        conda run -n $EnvName pip uninstall -y torch torchaudio
        Install-CpuTorch
    }
} else {
    Write-Host "Sem GPU NVIDIA detectada."
    Install-CpuTorch
}

Write-Host "== manim, sympy, coqui-tts =="
conda run -n $EnvName pip install -r "$Dir\requirements.txt"

Write-Host ""
Write-Host "Pronto. Para usar:"
Write-Host "  conda activate $EnvName"
Write-Host "Pra testar a renderização (sem áudio, rápido):"
Write-Host "  cd $Dir\motor; `$env:ROTEIRO='$Dir\roteiro_exemplo.json'; conda run -n $EnvName manim -ql --disable_caching -o teste render.py Aula"
Write-Host "Veja README.md para o passo a passo completo."
