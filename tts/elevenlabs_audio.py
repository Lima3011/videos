"""Gera áudio por passo do roteiro usando o ElevenLabs — alternativa ao Piper.

Troca-o-Piper-por-isto: produz exatamente os mesmos arquivos (passo_NN.wav + manifesto),
então o motor de render não muda em nada. A matemática continua verbalizada no campo
`narracao`; o TTS só recebe português.

Segredo: a chave vem de _video/.env (ELEVENLABS_API_KEY), NUNCA hardcoded — regra do
projeto. A voz é escolhida por ID no painel do ElevenLabs (Voice Library) e passada em
ELEVENLABS_VOICE_ID; sem clonagem, usa-se uma voz pré-pronta do catálogo.

Uso:  ELEVENLABS_VOICE_ID=<id> python elevenlabs_audio.py <roteiro.json>
"""
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

BASE = Path(__file__).parent
MODELO = os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2")


def carregar_env():
    env = BASE.parent / ".env"
    if env.exists():
        for linha in env.read_text().splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                k, v = linha.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def sintetizar(texto, chave, voice_id, destino_mp3):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    corpo = json.dumps({
        "text": texto,
        "model_id": MODELO,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75,
                           "style": 0.0, "use_speaker_boost": True},
    }).encode()
    req = urllib.request.Request(url, data=corpo, method="POST", headers={
        "xi-api-key": chave, "Content-Type": "application/json",
        "Accept": "audio/mpeg"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        destino_mp3.write_bytes(resp.read())


def dur(caminho):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(caminho)], capture_output=True, text=True).stdout
    return round(float(out.strip()), 2)


def main(roteiro):
    carregar_env()
    chave = os.environ.get("ELEVENLABS_API_KEY")
    voice = os.environ.get("ELEVENLABS_VOICE_ID")
    if not chave or not voice:
        sys.exit("Faltam ELEVENLABS_API_KEY (no _video/.env) e/ou ELEVENLABS_VOICE_ID.")

    r = json.load(open(roteiro))
    saida = BASE / "audio" / r["id"]
    saida.mkdir(parents=True, exist_ok=True)

    manifesto = []
    for i, p in enumerate(r["passos"]):
        narr = p.get("narracao")
        if not narr:
            manifesto.append({"passo": i, "wav": None, "dur": 0.0})
            continue
        mp3 = saida / f"passo_{i:02d}.mp3"
        wav = saida / f"passo_{i:02d}.wav"
        sintetizar(narr, chave, voice, mp3)
        # converte para wav (o motor usa wav; mantém compatível com o Piper)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(mp3),
                        "-ar", "22050", str(wav)], check=True)
        manifesto.append({"passo": i, "wav": str(wav), "dur": dur(wav)})

    json.dump(manifesto, open(saida / "manifesto.json", "w"),
              ensure_ascii=False, indent=1)
    n = len([m for m in manifesto if m["wav"]])
    print(f"{n} áudios via ElevenLabs ({MODELO}) | "
          f"fala total {sum(m['dur'] for m in manifesto):.0f}s")


if __name__ == "__main__":
    main(sys.argv[1])
