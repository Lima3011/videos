"""Teste comparativo: gera áudio via Fish Audio S2.1 Pro (API gratuita) — NÃO é o
motor de produção ainda, é só pra comparar naturalidade contra o XTTS-v2 local.

Ao contrário do xtts_audio.py, manda a `narracao` INTEIRA pro modelo, pontuação e
tudo (sem quebra por frase/cláusula) — o objetivo do teste é justamente ver se o S2
lida melhor com pontuação normal do que o XTTS, sem os contornos que criamos pra ele.

Segredo: a chave vem de _video/.env (FISH_API_KEY), NUNCA hardcoded — mesma regra do
elevenlabs_audio.py. Pegue a sua grátis em https://fish.audio/app/api-keys/ (sem
cartão de crédito). Acesso gratuito ao S2.1 Pro vale até 31/ago/2026 (fair use, sem
limite rígido de caracteres).

Uso:  python fish_audio_teste.py <roteiro.json> [passo1,passo2,...]
  (lista de índices de passo opcional — sem ela, gera todos os passos com narração)
"""
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

BASE = Path(__file__).parent
URL = "https://api.fish.audio/v1/tts"
MODELO = "s2.1-pro-free"
REFERENCE_ID = os.environ.get("FISH_REFERENCE_ID")  # None = voz padrão do modelo


def carregar_env():
    env = BASE.parent / ".env"
    if env.exists():
        for linha in env.read_text().splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                k, v = linha.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def sintetizar(texto, chave, destino_wav):
    corpo = {"text": texto, "format": "wav"}
    if REFERENCE_ID:
        corpo["reference_id"] = REFERENCE_ID
    req = urllib.request.Request(URL, data=json.dumps(corpo).encode(), method="POST",
                                  headers={"Authorization": f"Bearer {chave}",
                                           "Content-Type": "application/json",
                                           "model": MODELO})
    with urllib.request.urlopen(req, timeout=120) as resp:
        destino_wav.write_bytes(resp.read())


def dur(caminho):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(caminho)], capture_output=True, text=True).stdout
    return round(float(out.strip()), 2)


def main(roteiro, indices=None):
    carregar_env()
    chave = os.environ.get("FISH_API_KEY")
    if not chave:
        sys.exit("Falta FISH_API_KEY em _video/.env — pegue em https://fish.audio/app/api-keys/")

    r = json.load(open(roteiro))
    saida = BASE / "audio_fish_teste" / r["id"]
    saida.mkdir(parents=True, exist_ok=True)

    manifesto = []
    for i, p in enumerate(r["passos"]):
        if indices and i not in indices:
            continue
        narr = p.get("narracao")
        if not narr:
            continue
        wav = saida / f"passo_{i:02d}.wav"
        sintetizar(narr, chave, wav)
        manifesto.append({"passo": i, "wav": str(wav), "dur": dur(wav)})
        print(f"  passo {i}: {dur(wav)}s -> {wav.name}")

    json.dump(manifesto, open(saida / "manifesto.json", "w"), ensure_ascii=False, indent=1)
    print(f"{len(manifesto)} áudios via Fish Audio ({MODELO}) | "
          f"fala total {sum(m['dur'] for m in manifesto):.0f}s | pasta: {saida}")


if __name__ == "__main__":
    idx = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    main(sys.argv[1], idx)
