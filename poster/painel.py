"""Painel de arte vivo (zona de arte do ultrawide): a mesma arte do pôster + dados úteis.

render() é puro: recebe os dados já coletados e devolve a imagem; a janela (wl/painel_app.py) só exibe.
"""
from PIL import Image, ImageDraw

from layout import Rect
from poster import compor
from poster import modulos as m


MIN = (420, 700)  # abaixo disso desenha no mínimo e a janela escala (ContentFit.FILL)


def _barra(d, x, y, w, h, frac, pal):
    d.rectangle([x, y, x + w, y + h], outline=pal["borda"], fill=pal["fundo"])
    d.rectangle([x + 2, y + 2, x + 2 + round((w - 4) * max(0.0, min(1.0, frac))), y + h - 2], fill=pal["accent"])


def base(pal: dict, tamanho: tuple[int, int]) -> Image.Image:
    """Parte fixa (arte), desenhada uma vez por tamanho de janela."""
    w, h = max(MIN[0], tamanho[0]), max(MIN[1], tamanho[1])
    img = Image.new("RGB", (w, h), pal["fundo"])
    compor._grade(img, pal)
    compor._zona_arte(img, Rect(0, 0, w, h), pal, seed=7)
    topo = round(h * 0.645)
    ImageDraw.Draw(img).rectangle([0, topo, w - 110, h - 60], fill=pal["fundo"])  # sai o traceroute decorativo
    m.moldura(img, Rect(12, topo - 8, w - 128, h - 60 - topo), pal, chanfro=12)
    return img


def render(dados: dict, pal: dict, tamanho: tuple[int, int], tick: int, fixo: Image.Image | None = None) -> Image.Image:
    w, h = max(MIN[0], tamanho[0]), max(MIN[1], tamanho[1])
    img = (fixo or base(pal, (w, h))).copy()
    d = ImageDraw.Draw(img)
    topo, x = round(h * 0.645), 26
    g = dados.get
    m.titulo(img, (x, topo), g("hora", "--:--"), pal, 54)
    m.texto(img, (x + 4, topo + 66), f"{g('data', '')}  //  接続中", pal["foco"], "mono", 16)
    y = topo + 100
    m.texto(img, (x, y), "♪", pal["accent"], "cjk", 18)
    m.texto(img, (x + 26, y + 2), str(g("musica", "—"))[:38], pal["texto"], "mono", 16)
    _barra(d, x + 26, y + 26, w - 170, 8, float(g("progresso", 0) or 0), pal)
    linhas = [("NET", f"{g('ip', '—')}  {g('rede', '')}"), ("TEMP", g("temp", "—")),
              ("IA", g("ia", "—")), ("BKP", g("backup", "—")), ("ICE", g("alertas", "—"))]
    for i, (rot, val) in enumerate(linhas):
        yy = y + 48 + i * 24
        m.texto(img, (x, yy), rot, pal["foco"], "mono", 15)
        cor = pal["alerta"] if rot == "ICE" and str(val) != "ok" else pal["texto_4"]
        m.texto(img, (x + 64, yy), str(val)[:36], cor, "mono", 15)
    if tick % 9 == 0:  # glitch leve, de vez em quando
        y0 = (tick * 37) % (h - 20)
        faixa = img.crop((0, y0, w, y0 + 6))
        img.paste(faixa, (6 if tick % 2 else -6, y0))
    return img
