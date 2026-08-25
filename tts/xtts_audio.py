"""Gera áudio por passo do roteiro usando o Coqui XTTS-v2 — roda local, sem API paga.

Troca-o-ElevenLabs-por-isto: produz exatamente os mesmos arquivos (passo_NN.wav +
manifesto.json), então o motor de render (render.py) não muda em nada. A matemática
continua verbalizada em português no campo `narracao`; o TTS só recebe texto comum,
igual ao Piper e ao ElevenLabs.

XTTS-v2 é multilíngue e roda com uma voz pronta da própria biblioteca (sem precisar
clonar nada) — basta escolher o nome do locutor com XTTS_SPEAKER. Se preferir clonar
uma voz específica no futuro, passe XTTS_SPEAKER_WAV apontando para uma amostra de
10-30s; quando essa variável existe ela tem prioridade sobre XTTS_SPEAKER.

Licença: o modelo XTTS-v2 é distribuído sob a CPML (Coqui Public Model License), que
permite uso não-comercial livremente; uso comercial requer licença da Coqui. Confirme
os termos (https://coqui.ai/cpml) antes de publicar vídeos monetizados com essa voz.

Ajuste fino: XTTS_SPEED controla o ritmo (>1 mais rápido, <1 mais devagar — o motor
de render lê a duração REAL do áudio gerado, então mudar a velocidade nunca desalinha
o vídeo). XTTS_TEMPERATURE controla a variação de entonação (mais alto soa menos
"robotizado", mas alto demais pode ficar instável).

Pontuação: o XTTS-v2 em português às vezes LÊ sinais de pontuação em voz alta (ponto,
dois-pontos vira "ponto", "dois pontos" falado) em vez de tratá-los como pausa muda —
é uma limitação conhecida do modelo, não bug deste script. Por isso a síntese aqui
NUNCA manda pontuação pro modelo: o texto é quebrado em frases e, se alguma frase for
longa, também em cláusulas por vírgula — cada pedaço é sintetizado SEM pontuação de
borda e colado ao seguinte com um silêncio de verdade (áudio, não pontuação). Isso
também evita um problema maior que só cortar pontuação: pedaço de texto muito longo
faz o XTTS "fugir" do que devia ler (parafrasear/inventar) ou engasgar no fim de
números grandes — textos curtos são muito mais estáveis. Ainda assim, escreva a
`narracao` sem `:`/`;`/`a)` (o roteiro fica mais legível pro professor conferir).

Uso:  XTTS_SPEAKER="Viktor Eka" python xtts_audio.py <roteiro.json>
"""
import json
import os
import re
import shutil
import sys
import wave
from pathlib import Path

os.environ.setdefault("COQUI_TOS_AGREED", "1")  # aceite da CPML p/ baixar o modelo sem prompt

BASE = Path(__file__).parent
MODELO = "tts_models/multilingual/multi-dataset/xtts_v2"

IDIOMA = os.environ.get("XTTS_LANGUAGE", "pt")
# "Luis Moray" venceu a comparação de vozes prontas do XTTS (ver
# tts/amostras_vozes/) — soou mais natural e menos "de IA" que a antiga (Viktor Eka)
LOCUTOR = os.environ.get("XTTS_SPEAKER", "Luis Moray")
LOCUTOR_WAV = os.environ.get("XTTS_SPEAKER_WAV")  # amostra p/ clonagem; opcional
# o padrão do XTTS (1.0) narra devagar demais pra um vídeo de resolução — 1.1
# tira esse arrasto sem soar apressado nem distorcer a voz
VELOCIDADE = float(os.environ.get("XTTS_SPEED", "1.1"))
# temperatura mais alta = mais variação de entonação (menos "robotizado"), mas
# também mais chance de glitch (fugir do texto, engasgar em número longo, trocar
# "carro" por "caro"). Pra vídeo de aula, clareza importa mais que expressividade
# — 0.5 prioriza estabilidade; o padrão do XTTS é 0.75
TEMPERATURA = float(os.environ.get("XTTS_TEMPERATURE", "0.5"))
# frase mais longa que isso (em caracteres) também quebra em cláusulas por
# vírgula — pedaço curto é mais estável no XTTS que uma frase inteira longa
LIMITE_CLAUSULA = int(os.environ.get("XTTS_LIMITE_CLAUSULA", "90"))
# pausas entre pedaços, em ms — mais longa entre frases, mais curta entre
# cláusulas da mesma frase, pra imitar a respiração natural de quem lê em voz
# alta, sem depender do XTTS interpretar pontuação nenhuma
PAUSA_FRASE_MS = int(os.environ.get("XTTS_PAUSA_MS", "380"))
PAUSA_CLAUSULA_MS = int(os.environ.get("XTTS_PAUSA_CLAUSULA_MS", "100"))
# fragmento de cláusula mais curto que isso (em caracteres) é fundido de volta
# no vizinho — evita isolar sozinho um pedaço tipo "n menos um" ou "quatro",
# que soa como corte brusco sem motivo (combinação/coordenada/opções são os
# casos mais comuns disso, por causa da vírgula "de notação" que não é pausa
# de prosa de verdade)
LIMITE_FRAGMENTO_MIN = int(os.environ.get("XTTS_LIMITE_FRAGMENTO_MIN", "25"))
# >1 desencoraja o modelo a parar cedo demais — combate leitura "truncada" em
# frases numéricas longas (ex. números por extenso), que tendem a cortar o
# final; o padrão do XTTS é 1.0
LENGTH_PENALTY = float(os.environ.get("XTTS_LENGTH_PENALTY", "1.3"))


def carregar_modelo():
    import torch
    from TTS.api import TTS
    dispositivo = os.environ.get("XTTS_DEVICE") or ("cuda" if torch.cuda.is_available() else "cpu")
    return TTS(MODELO, progress_bar=False).to(dispositivo)


def dur(caminho):
    with wave.open(str(caminho)) as w:
        return round(w.getnframes() / w.getframerate(), 2)


def clausulas(texto):
    """Quebra em frases e, se alguma ficar longa demais, quebra também nas
    vírgulas — pedaço curto é o que dá pro XTTS ler com estabilidade. Cada item
    volta como (texto_sem_pontuação, tipo_da_pausa_que_vem_depois), pra colar
    cláusulas da mesma frase com pausa curta e frases diferentes com pausa longa.
    """
    texto = re.sub(r"[:;]", ",", texto.strip())
    sentencas = [s.strip() for s in re.split(r"(?<=[.!?])\s+", texto) if s.strip()]
    saida = []
    for s in sentencas:
        limpa = s.strip(" .!?")
        if not limpa:
            continue
        if len(limpa) <= LIMITE_CLAUSULA or "," not in limpa:
            saida.append((limpa, "frase"))
            continue
        partes = [p.strip() for p in limpa.split(",") if p.strip()]
        # funde fragmento curto demais no vizinho — nunca isola sozinho um
        # pedaço tipo "n menos um" (ver LIMITE_FRAGMENTO_MIN acima)
        fundidas = []
        for p in partes:
            if fundidas and len(p) < LIMITE_FRAGMENTO_MIN:
                fundidas[-1] = f"{fundidas[-1]} {p}"
            else:
                fundidas.append(p)
        if len(fundidas) > 1 and len(fundidas[0]) < LIMITE_FRAGMENTO_MIN:
            fundidas[1] = f"{fundidas[0]} {fundidas[1]}"
            fundidas.pop(0)
        for i, p in enumerate(fundidas):
            saida.append((p, "frase" if i == len(fundidas) - 1 else "clausula"))
    return saida


def _aparar(clipe, fade_ms=120):
    """Corta só silêncio de VERDADE nas pontas e suaviza o final com fade-out
    suave (sem remover frames extras no fade, só volume).

    Cuidado de propósito: um limiar agressivo aqui corta a fala de verdade,
    não só o ruído — o final de uma palavra (principalmente números longos
    por extenso) natural decai de volume antes de acabar, e um corte cedo
    demais soa "truncado". -40dB relativo é conservador, só remove silêncio
    real; quem cuida do artefato de cauda esquisita é o length_penalty na
    síntese, não corte de áudio.
    """
    from pydub.silence import detect_leading_silence
    limiar = clipe.dBFS - 40 if clipe.dBFS > -60 else -45
    inicio = detect_leading_silence(clipe, silence_threshold=limiar)
    fim = detect_leading_silence(clipe.reverse(), silence_threshold=limiar)
    if len(clipe) - fim > inicio:
        clipe = clipe[inicio: len(clipe) - fim]
    return clipe.fade_out(min(fade_ms, len(clipe)))


def sintetizar_passo(tts, texto, destino, kw):
    from pydub import AudioSegment

    tmp_dir = destino.parent / f".tmp_{destino.stem}"
    tmp_dir.mkdir(exist_ok=True)
    try:
        silencio = {"frase": AudioSegment.silent(duration=PAUSA_FRASE_MS),
                    "clausula": AudioSegment.silent(duration=PAUSA_CLAUSULA_MS)}
        final, pausa_antes = None, None
        for i, (pedaco, tipo_apos) in enumerate(clausulas(texto)):
            tmp = tmp_dir / f"{i}.wav"
            tts.tts_to_file(text=pedaco, language=IDIOMA, speed=VELOCIDADE,
                             temperature=TEMPERATURA, length_penalty=LENGTH_PENALTY,
                             file_path=str(tmp), **kw)
            trecho = _aparar(AudioSegment.from_wav(tmp))
            final = trecho if final is None else final + silencio[pausa_antes] + trecho
            pausa_antes = tipo_apos
        final.export(destino, format="wav")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def main(roteiro):
    tts = carregar_modelo()

    r = json.load(open(roteiro))
    saida = BASE / "audio" / r["id"]
    saida.mkdir(parents=True, exist_ok=True)

    kw = {"speaker_wav": LOCUTOR_WAV} if LOCUTOR_WAV else {"speaker": LOCUTOR}

    manifesto = []
    for i, p in enumerate(r["passos"]):
        narr = p.get("narracao")
        if not narr:
            manifesto.append({"passo": i, "wav": None, "dur": 0.0})
            continue
        wav = saida / f"passo_{i:02d}.wav"
        sintetizar_passo(tts, narr, wav, kw)
        manifesto.append({"passo": i, "wav": str(wav), "dur": dur(wav)})

    json.dump(manifesto, open(saida / "manifesto.json", "w"),
              ensure_ascii=False, indent=1)
    n = len([m for m in manifesto if m["wav"]])
    voz = LOCUTOR_WAV or LOCUTOR
    print(f"{n} áudios via XTTS-v2 (voz: {voz}) | "
          f"fala total {sum(m['dur'] for m in manifesto):.0f}s")


if __name__ == "__main__":
    main(sys.argv[1])
