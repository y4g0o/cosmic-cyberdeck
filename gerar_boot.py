"""Gera a tela de boot (Plymouth) no estilo cyberdeck: o tema pop-basic com as cores da paleta e a assinatura do config.toml.

Mantém o módulo two-step e as imagens do diálogo de senha do Pop; só troca cores e a imagem central.
Uso: python3 gerar_boot.py   -> grava saida/plymouth/cyberdeck e saida/plymouth/INSTALAR-BOOT.sh (rodar com sudo)
"""
import re
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import marca
import paleta
from poster import modulos

RAIZ = Path(__file__).resolve().parent
POP = Path("/usr/share/plymouth/themes/pop-basic")
DESTINO = "/usr/share/plymouth/themes/cyberdeck"
TAM = (200, 250)   # mesmo tamanho da imagem do Pop
LEGENDA = ("起動シーケンス", "POP!_OS · COSMIC")


def _hex(cor):
    return "0x" + cor.lstrip("#").lower()


def _marca(pal):
    img = Image.new("RGBA", TAM, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w, h = TAM
    roxo, verde = paleta.hex_rgb(pal["foco"]), paleta.hex_rgb(pal["accent"])
    for x, y, dx, dy in ((14, 40, 1, 1), (w - 15, 40, -1, 1), (14, h - 60, 1, -1), (w - 15, h - 60, -1, -1)):
        d.line([(x, y), (x + 22 * dx, y)], fill=roxo, width=2)   # cantoneiras
        d.line([(x, y), (x, y + 22 * dy)], fill=roxo, width=2)
    nome, tam = marca.assinatura(), 46
    while tam > 12 and d.textlength(nome, font=modulos._fonte("dela", tam)) > w - 36:
        tam -= 2   # assinatura longa: encolhe até caber entre as cantoneiras
    f = modulos._fonte("dela", tam)
    caixa = d.textbbox((0, 0), nome, font=f)
    d.text(((w - (caixa[2] - caixa[0])) / 2 - caixa[0], 104 - (caixa[1] + caixa[3]) / 2), nome, font=f, fill=verde)
    d.line([(40, 152), (w - 40, 152)], fill=roxo, width=1)
    f2 = modulos._fonte("dot", 13)
    for i, txt in enumerate(LEGENDA):
        cx = d.textbbox((0, 0), txt, font=f2)
        d.text(((w - (cx[2] - cx[0])) / 2, 162 + 18 * i), txt, font=f2, fill=paleta.hex_rgb(pal["texto"]))
    return img


def _plymouth(pal):
    t = (POP / "pop-basic.plymouth").read_text()
    t = t.replace("Name=Pop Basic", "Name=cyberdeck").replace(str(POP), DESTINO)
    t = re.sub(r"Description=.*", "Description=cosmic-cyberdeck boot screen (two-step with the palette colors).", t)
    for chave, cor in (("BackgroundStartColor", "fundo"), ("BackgroundEndColor", "fundo"),
                       ("ProgressBarBackgroundColor", "roxo_profundo"), ("ProgressBarForegroundColor", "accent")):
        t = re.sub(rf"{chave}=.*", f"{chave}={_hex(pal[cor])}", t)
    return t


def gerar(pasta, pal):
    tema = Path(pasta) / "cyberdeck"
    shutil.rmtree(tema, ignore_errors=True)
    tema.mkdir(parents=True)
    for f in POP.iterdir():
        if f.suffix == ".png" and not f.is_symlink():
            shutil.copy(f, tema / f.name)
    _marca(pal).save(tema / "header-image.png")
    shutil.copy(tema / "header-image.png", tema / "bgrt-fallback.png")
    (tema / "cyberdeck.plymouth").write_text(_plymouth(pal))
    return tema


def script_instalar():
    return f"""#!/bin/bash
# Tela de boot cyberdeck. Uso: sudo bash INSTALAR-BOOT.sh   |   desfazer: sudo bash INSTALAR-BOOT.sh --desfazer
set -e
cd "$(dirname "$0")"
if [ "$1" = "--desfazer" ]; then
  update-alternatives --set default.plymouth {POP}/pop-basic.plymouth
  update-alternatives --remove default.plymouth {DESTINO}/cyberdeck.plymouth || true
  rm -rf {DESTINO}
else
  rm -rf {DESTINO}
  cp -r cyberdeck {DESTINO}
  update-alternatives --install /usr/share/plymouth/themes/default.plymouth default.plymouth {DESTINO}/cyberdeck.plymouth 100
  update-alternatives --set default.plymouth {DESTINO}/cyberdeck.plymouth
fi
update-initramfs -u
echo "pronto: vale no próximo boot"
"""


def main(argv):
    pasta = RAIZ / "saida/plymouth"
    tema = gerar(pasta, paleta.carregar())
    (pasta / "INSTALAR-BOOT.sh").write_text(script_instalar())
    print(f"gerado: {tema}\ninstale com: sudo bash {pasta / 'INSTALAR-BOOT.sh'}")


if __name__ == "__main__":
    main(sys.argv[1:])
