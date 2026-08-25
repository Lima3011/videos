"""Gera um arquivo de áudio por passo do roteiro, a partir do campo `narracao`.

O ponto que resolve o "TTS não entende matemática": o TTS NUNCA vê fórmula. O campo
`narracao` do roteiro já traz a matemática verbalizada em português ("nove meios vezes
dois ao cubo"), escrita por quem planejou a resolução. O TTS só lê texto comum.

Salva tts/audio/<id>/passo_NN.wav e um manifesto com a duração real de cada áudio,
que o renderizador usa para fazer cada cena durar o tempo da fala — sincronia por
construção, não por estimativa.

Uso: gerar_audio.py <roteiro.json>
"""
import json
import os
import sys
import wave
from pathlib import Path

from piper import PiperVoice
try:
    from piper import SynthesisConfig
except Exception:
    SynthesisConfig = None

# voz e ritmo configuráveis: VOZ=faber|cadu|jeff  LENGTH_SCALE=1.3 (>1 = mais devagar)
NOME_VOZ = os.environ.get("VOZ", "faber")
LENGTH = float(os.environ.get("LENGTH_SCALE", "1.3"))


def main(roteiro):
    r = json.load(open(roteiro))
    voz = PiperVoice.load(str(Path(__file__).parent / f"{NOME_VOZ}.onnx"))
    cfg = SynthesisConfig(length_scale=LENGTH) if SynthesisConfig else None
    saida = Path(__file__).parent / "audio" / r["id"]
    saida.mkdir(parents=True, exist_ok=True)

    manifesto = []
    for i, p in enumerate(r["passos"]):
        narr = p.get("narracao")
        if not narr:
            manifesto.append({"passo": i, "wav": None, "dur": 0.0})
            continue
        wav_path = saida / f"passo_{i:02d}.wav"
        with wave.open(str(wav_path), "wb") as w:
            if cfg:
                voz.synthesize_wav(narr, w, syn_config=cfg)
            else:
                voz.synthesize_wav(narr, w)
        with wave.open(str(wav_path)) as w:
            dur = w.getnframes() / w.getframerate()
        manifesto.append({"passo": i, "wav": str(wav_path), "dur": round(dur, 2)})

    man_path = saida / "manifesto.json"
    json.dump(manifesto, open(man_path, "w"), ensure_ascii=False, indent=1)
    total = sum(m["dur"] for m in manifesto)
    print(f"{len([m for m in manifesto if m['wav']])} áudios | fala total {total:.0f}s")
    print(f"manifesto: {man_path}")


if __name__ == "__main__":
    main(sys.argv[1])
