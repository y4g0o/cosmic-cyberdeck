"""Gera o tema de sons cyberdeck (freedesktop) por síntese: bipes curtos e graves, timbre macio, nada longo.

Uso: python3 gerar_sons.py [--instalar]
  sem opção: grava em saida/sons/ para ouvir (paplay saida/sons/cyberdeck/stereo/complete.oga)
  --instalar: copia para ~/.local/share/sounds/cyberdeck e põe como tema de sons. O volume do COSMIC (cosmic-osd)
  procura o arquivo fixo freedesktop/stereo/audio-volume-change.oga, por isso ele ganha um link na pasta do usuário.
"""
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

TAXA = 48000
PICO = 0.35
RAIZ = Path(__file__).resolve().parent
DESTINO = Path.home() / ".local/share/sounds"


def _tom(f0, f1, dur, forma="suave"):
    """Varredura de f0 a f1 Hz com envelope curto. Formas com poucos harmônicos (sem onda quadrada nem
    bitcrush, que deixavam tudo agudo): suave = seno com um pouco de 2º e 3º harmônico; serra = 4 harmônicos."""
    n = int(TAXA * dur)
    fase = 2 * np.pi * np.cumsum(np.geomspace(f0, f1, n)) / TAXA
    if forma == "seno":
        onda = np.sin(fase)
    elif forma == "serra":
        onda = sum(np.sin(k * fase) / k for k in range(1, 5))
    elif forma == "ruido":   # ruído por 3 médias móveis (corta o chiado), modulado pela varredura
        ruido = np.random.default_rng(int(f0)).uniform(-1, 1, n)
        for _ in range(3):
            ruido = np.convolve(ruido, np.ones(48) / 48, mode="same")
        onda = ruido * (0.6 + 0.4 * np.sin(fase))
    else:
        onda = np.sin(fase) + 0.25 * np.sin(2 * fase) + 0.1 * np.sin(3 * fase)
    ataque = min(int(TAXA * 0.006), n // 4)
    env = np.exp(-np.linspace(0, 4, n))
    env[:ataque] *= np.linspace(0, 1, ataque)
    env[-1] = 0.0
    return onda * env


def _pausa(dur):
    return np.zeros(int(TAXA * dur))


def _seq(*partes):
    return np.concatenate(partes)


EVENTOS = {
    "audio-volume-change": lambda: _tom(660, 660, 0.05, "seno"),
    "bell": lambda: _seq(_tom(660, 660, 0.07), _tom(440, 440, 0.11)),
    "complete": lambda: _seq(_tom(330, 330, 0.07), _tom(440, 440, 0.07), _tom(660, 660, 0.14)),
    "message-new-instant": lambda: _seq(_tom(494, 494, 0.06), _pausa(0.03), _tom(740, 740, 0.09)),
    "message": lambda: _seq(_tom(494, 494, 0.06), _pausa(0.03), _tom(740, 740, 0.09)),
    "window-attention": lambda: _seq(*[_seq(_tom(600, 600, 0.05), _pausa(0.04)) for _ in range(3)]),
    "dialog-information": lambda: _tom(440, 440, 0.14, "seno"),
    "dialog-warning": lambda: _seq(_tom(220, 220, 0.09, "serra"), _pausa(0.04), _tom(220, 220, 0.09, "serra")),
    "dialog-error": lambda: _tom(196, 110, 0.28, "serra"),
    "device-added": lambda: _tom(220, 800, 0.16),
    "device-removed": lambda: _tom(800, 220, 0.19),
    "screen-capture": lambda: _seq(_tom(900, 900, 0.02, "ruido"), _tom(700, 200, 0.09, "ruido")),
    "camera-shutter": lambda: _seq(_tom(900, 900, 0.02, "ruido"), _tom(700, 200, 0.09, "ruido")),
    "trash-empty": lambda: _tom(800, 120, 0.3, "ruido"),
    "service-login": lambda: _seq(*[_tom(f, f, 0.07) for f in (220, 330, 440, 660)]),
    "service-logout": lambda: _seq(*[_tom(f, f, 0.07) for f in (660, 440, 330, 220)]),
    "network-connectivity-established": lambda: _seq(_tom(350, 350, 0.07), _tom(700, 700, 0.1)),
    "network-connectivity-lost": lambda: _seq(_tom(700, 700, 0.07), _tom(350, 350, 0.13, "serra")),
}


def sintetizar(nome):
    onda = EVENTOS[nome]()
    return (onda * (PICO / np.abs(onda).max())).astype(np.float32)


def index_theme():
    return ("[Sound Theme]\nName=cyberdeck\nComment=Bipes digitais do cyberdeck\nInherits=freedesktop\nDirectories=stereo\n\n"
            "[stereo]\nOutputProfile=stereo\n")


def gerar(pasta):
    tema = pasta / "cyberdeck"
    (tema / "stereo").mkdir(parents=True, exist_ok=True)
    (tema / "index.theme").write_text(index_theme())
    with tempfile.TemporaryDirectory() as tmp:
        for nome in EVENTOS:
            wav = Path(tmp) / f"{nome}.wav"
            with wave.open(str(wav), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(TAXA)
                w.writeframes((sintetizar(nome) * 32767).astype("<i2").tobytes())
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(wav), "-c:a", "libvorbis", "-q:a", "4",
                            str(tema / "stereo" / f"{nome}.oga")], check=True)
    return tema


def instalar(tema):
    alvo = DESTINO / "cyberdeck"
    shutil.rmtree(alvo, ignore_errors=True)
    shutil.copytree(tema, alvo)
    vol = DESTINO / "freedesktop/stereo/audio-volume-change.oga"
    vol.parent.mkdir(parents=True, exist_ok=True)
    vol.unlink(missing_ok=True)
    vol.symlink_to(alvo / "stereo/audio-volume-change.oga")
    subprocess.run(["gsettings", "set", "org.gnome.desktop.sound", "theme-name", "cyberdeck"], check=True)


def main(argv):
    tema = gerar(RAIZ / "saida/sons")
    print(f"gerado: {tema} ({len(EVENTOS)} sons)")
    if "--instalar" in argv:
        instalar(tema)
        print("instalado: tema de sons = cyberdeck")


if __name__ == "__main__":
    main(sys.argv[1:])
