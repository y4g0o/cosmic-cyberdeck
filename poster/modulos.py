"""Modulos graficos do poster: paineis de dossie, dither 1-bit, ficha, barras, ondas, circuitos."""
import random
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont

from layout import Rect

TEXTOS_PROIBIDOS = ["cyberpunk", "2077", "edgerunner", "arasaka", "night city", "samurai", "militech"]

FUNDO_PADRAO = "#060609"
_RAIZ = Path(__file__).resolve().parent.parent
# onde procurar as fontes, em ordem: as que vêm no repositório (todas SIL OFL, licenças ao lado) e as instaladas
PASTAS_FONTES = [_RAIZ / "fontes", _RAIZ / "brave-ntp/fontes", Path.home() / ".local/share/fonts/cosmic-cyberdeck",
                 Path.home() / ".local/share/fonts", Path("/usr/share/fonts/opentype/noto"),
                 Path("/usr/share/fonts/opentype/noto-cjk"), Path("/usr/share/fonts/truetype")]
_NOMES = {
    "orbitron": "Orbitron.ttf",
    "dot": "DotGothic16-Regular.ttf",
    "dela": "DelaGothicOne-Regular.ttf",
    "mono": "ShareTechMono-Regular.ttf",
    "cjk": "NotoSansCJK-Bold.ttc",   # pacote fonts-noto-cjk (já vem no Pop!_OS)
}


def caminho_fonte(nome: str) -> Path | None:
    """Arquivo da fonte `nome` (orbitron|dot|dela|mono|cjk) na primeira pasta que a tiver, ou None."""
    for pasta in PASTAS_FONTES:
        p = pasta / _NOMES[nome]
        if p.exists():
            return p
    return None


def fontes_faltando() -> list[str]:
    return [_NOMES[n] for n in _NOMES if caminho_fonte(n) is None]

# Registro de todo texto desenhado (permite auditar o conteudo nos testes).
_LOG_TEXTOS: list[str] = []


def validar_texto(s: str) -> str:
    baixo = s.lower()
    for p in TEXTOS_PROIBIDOS:
        if p in baixo:
            raise ValueError(f"texto proibido: {p!r} em {s!r}")
    return s


@lru_cache(maxsize=None)
def _fonte(nome: str, tamanho: int) -> ImageFont.FreeTypeFont:
    p = caminho_fonte(nome)
    if p is None:
        raise OSError(f"fonte {_NOMES[nome]} não encontrada (veja a seção Requirements do README)")
    f = ImageFont.truetype(str(p), tamanho)
    if nome == "orbitron":
        try:
            f.set_variation_by_axes([700])
        except Exception:
            pass
    return f


def _texto(img, xy, s, fonte, fill, ancora="la"):
    """Unico ponto por onde todo texto e desenhado."""
    validar_texto(s)
    _LOG_TEXTOS.append(s)
    ImageDraw.Draw(img).text(xy, s, font=fonte, fill=fill, anchor=ancora)


def _fonte_para(s: str, fonte: str) -> str:
    """Fontes latinas (mono/orbitron) não têm japonês: troca para DotGothic16 se houver CJK no texto."""
    if fonte in ("mono", "orbitron") and any(ord(c) >= 0x2E80 or 0x2190 <= ord(c) <= 0x21FF for c in s):
        return "dot"
    return fonte


def texto(img, xy, s: str, cor: str, fonte: str = "mono", tamanho: int = 14, ancora: str = "la"):
    """Texto livre (valida termos proibidos). fonte: orbitron|dot|dela|mono|cjk."""
    _texto(img, xy, s, _fonte(_fonte_para(s, fonte), tamanho), cor, ancora)


def texto_vertical(img, xy, s: str, cor: str, fonte: str = "cjk", tamanho: int = 40, espaco: float = 1.08):
    """Escrita vertical (縦書き): um caractere por linha."""
    validar_texto(s)
    f = _fonte(fonte, tamanho)
    x, y = xy
    for i, ch in enumerate(s):
        _texto(img, (x, y + round(i * tamanho * espaco)), ch, f, cor)


def _mix(a: str, b: str, t: float) -> str:
    ca, cb = (int(a[i:i + 2], 16) for i in (1, 3, 5)), (int(b[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02X%02X%02X" % tuple(round(x + (y - x) * t) for x, y in zip(ca, cb))


def _chanfro_pts(r: Rect, c: int):
    x0, y0, x1, y1 = r.x, r.y, r.x + r.w - 1, r.y + r.h - 1
    return [(x0 + c, y0), (x1, y0), (x1, y1 - c), (x1 - c, y1), (x0, y1), (x0, y0 + c)]


def moldura(img, rect: Rect, pal: dict, chanfro: int = 12):
    """Moldura fina com cantos superior-esquerdo e inferior-direito chanfrados e tiques de canto."""
    d = ImageDraw.Draw(img)
    pts = _chanfro_pts(rect, chanfro)
    d.line(pts + [pts[0]], fill=_mix(pal["fundo"], pal["foco"], 0.7), width=1)
    x0, y0, x1, y1 = rect.x, rect.y, rect.x + rect.w - 1, rect.y + rect.h - 1
    t = max(6, chanfro)
    d.line([(x1 - t, y0), (x1, y0), (x1, y0 + t)], fill=pal["accent"], width=2)
    d.line([(x0, y1 - t), (x0, y1), (x0 + t, y1)], fill=pal["accent"], width=2)
    d.line([(x0 + chanfro, y0 - 3), (x0 + chanfro + 14, y0 - 3)], fill=pal["accent"], width=1)


def dither(img_fonte: Image.Image, rect: Rect, cor: str, fundo: str = FUNDO_PADRAO,
           centro: tuple[float, float] = (0.5, 0.3)) -> Image.Image:
    """Floyd-Steinberg 1-bit, colorizado: so `fundo` e `cor`. A foto e recortada (nao esticada) para caber,
    puxando para cima (padrao) para nao cortar cabecas; `centro` muda o foco do recorte."""
    g = ImageOps.fit(img_fonte.convert("L"), (rect.w, rect.h), Image.LANCZOS, centering=centro)
    bw = g.convert("1", dither=Image.FLOYDSTEINBERG)
    out = Image.new("RGB", (rect.w, rect.h), fundo)
    out.paste(Image.new("RGB", (rect.w, rect.h), cor), mask=bw)
    return out


def placeholder_foto(rect: Rect, seed: int) -> Image.Image:
    """Forma procedural em tons de cinza para o dither quando não há imagem: anéis concêntricos (tipo
    impressão digital) sobre um degradê com faixas de sinal. Abstrata de propósito: nenhuma figura humana."""
    rng = random.Random(seed)
    w, h = rect.w, rect.h
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    base = 40 + 60 * (xx / max(w, 1)) + 25 * np.sin(yy / max(h, 1) * np.pi * rng.uniform(2, 5))
    cx, cy = w * rng.uniform(0.35, 0.65), h * rng.uniform(0.35, 0.65)
    raio = np.hypot((xx - cx) / max(w, 1), (yy - cy) / max(h, 1))
    aneis = (np.sin(raio * rng.uniform(55, 80)) > 0.2) & (raio < 0.42)
    base = np.where(aneis, 205, base)
    im = Image.fromarray(np.clip(base, 0, 255).astype("uint8"), "L")
    d = ImageDraw.Draw(im)
    for _ in range(4):
        y = rng.randint(0, h)
        d.rectangle([0, y, w, y + rng.randint(1, 4)], fill=rng.randint(0, 90))
    return im


def codigo_barras(img, rect: Rect, pal: dict, seed: int):
    rng = random.Random(seed)
    d = ImageDraw.Draw(img)
    x, fim = rect.x, rect.x + rect.w
    while x < fim:
        w = rng.choice([1, 1, 2, 3, 4])
        if rng.random() < 0.6:
            d.rectangle([x, rect.y, min(x + w - 1, fim - 1), rect.y + rect.h - 1], fill=pal["texto"])
        x += w + rng.choice([1, 2, 2, 3])


def onda(img, rect: Rect, pal: dict, seed: int):
    rng = np.random.default_rng(seed)
    d = ImageDraw.Draw(img)
    n = rect.w
    cor_grade = _mix(pal["fundo"], pal["roxo_profundo"], 0.65)
    for gx in range(rect.x, rect.x + n, max(12, n // 16)):
        d.line([(gx, rect.y), (gx, rect.y + rect.h - 1)], fill=cor_grade, width=1)
    for gy in (rect.y + rect.h // 4, rect.y + (rect.h * 3) // 4):
        d.line([(rect.x, gy), (rect.x + n - 1, gy)], fill=cor_grade, width=1)
    d.rectangle([rect.x, rect.y, rect.x + n - 1, rect.y + rect.h - 1], outline=pal["roxo_profundo"], width=1)
    t = np.arange(n)
    f1, f2, f3 = rng.uniform(0.02, 0.06), rng.uniform(0.08, 0.2), rng.uniform(0.3, 0.6)
    env = 0.5 + 0.5 * np.sin(t * rng.uniform(0.01, 0.03) + rng.uniform(0, 6))
    y = (np.sin(t * f1) * .5 + np.sin(t * f2) * .3 * env + np.sin(t * f3) * .2 * rng.random(n)) * 0.9
    y2 = np.sin(t * (f1 * 0.85) + 1.4) * 0.55 * env
    mid = rect.y + rect.h / 2
    pts2 = [(rect.x + i, mid - v * rect.h / 2 * 0.85) for i, v in enumerate(y2)]
    pts = [(rect.x + i, mid - v * rect.h / 2 * 0.90) for i, v in enumerate(y)]
    d.line([(rect.x, mid), (rect.x + rect.w - 1, mid)], fill=pal["roxo_profundo"], width=1)
    d.line(pts2, fill=_mix(pal["fundo"], pal["foco"], 0.75), width=1)
    d.line(pts, fill=pal["accent"], width=1)
    for i in range(0, n, max(8, n // 12)):
        d.line([(rect.x + i, rect.y + rect.h - 4), (rect.x + i, rect.y + rect.h - 1)], fill=pal["foco"])


_VOCAB = ["SYS", "LNK", "NODE", "SYNC", "BUF", "PKT", "RX", "TX", "CORE", "MEM", "ACK", "NULL",
          "SCAN", "AUTH", "VECTOR", "PHASE", "GRID", "RELAY", "TRACE", "LOCK"]


def microtexto(img, rect: Rect, pal: dict, seed: int):
    rng = random.Random(seed)
    f = _fonte("mono", 9)
    y = rect.y
    cor = _mix(pal["fundo"], pal["circuito"], 0.75)
    while y + 10 <= rect.y + rect.h:
        linha = " ".join(
            rng.choice(_VOCAB) + ":" + "%04X" % rng.randrange(65536) for _ in range(max(1, rect.w // 70)))
        _texto(img, (rect.x, y), linha, f, cor)
        y += 11


def circuito(img, rect: Rect, pal: dict, seed: int, entradas: list[tuple[int, int]]):
    """Trilhas 45/90 graus ligando as `entradas` em sequencia, com pads redondos; mais ramais decorativos."""
    rng = random.Random(seed)
    d = ImageDraw.Draw(img)
    cor = pal["circuito"]

    def rota(a, b, horiz_primeiro):
        (x0, y0), (x1, y1) = a, b
        dx, dy = x1 - x0, y1 - y0
        s = min(abs(dx), abs(dy))
        sx, sy = (dx > 0) - (dx < 0), (dy > 0) - (dy < 0)
        diag = (x0 + sx * s, y0 + sy * s)
        if horiz_primeiro:
            meio = (x0 + (dx - sx * s), y0) if abs(dx) > s else (x0, y0 + (dy - sy * s))
        else:
            meio = (x0, y0 + (dy - sy * s)) if abs(dy) > s else (x0 + (dx - sx * s), y0)
        # reta -> diagonal: reta primeiro ate `meio`, depois diagonal ate b
        return [a, meio, b] if meio != a else [a, diag, b]

    pontos = list(entradas)
    for a, b in zip(pontos, pontos[1:]):
        d.line(rota(a, b, rng.random() < 0.5), fill=cor, width=2, joint="curve")
    for _ in range(max(3, rect.w * rect.h // 12000)):
        x, y = rng.randint(rect.x, rect.x + rect.w - 1), rng.randint(rect.y, rect.y + rect.h - 1)
        ang = rng.choice([(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)])
        n = rng.randint(15, 60)
        x2 = min(max(x + ang[0] * n, rect.x), rect.x + rect.w - 1)
        y2 = min(max(y + ang[1] * n, rect.y), rect.y + rect.h - 1)
        d.line([(x, y), (x2, y2)], fill=_mix(pal["fundo"], cor, 0.6), width=1)
        d.ellipse([x2 - 3, y2 - 3, x2 + 3, y2 + 3], outline=_mix(pal["fundo"], cor, 0.6))
    for (x, y) in pontos:
        d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=pal["fundo"], outline=pal["accent"], width=2)
        d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=pal["accent"])


def titulo(img, xy: tuple[int, int], texto: str, pal: dict, tamanho: int):
    _texto(img, xy, texto, _fonte("orbitron", tamanho), pal["accent"])


_CAMPOS = ["NAME", "FUNCTION", "STATE", "CLEARANCE", "LOCATION"]


def ficha_operador(img, rect: Rect, pal: dict, dados: dict, foto: Image.Image | None = None):
    """Cartao de identificacao: emblema dither a esquerda (imagem opcional), campos a direita, barras embaixo."""
    for v in dados.values():
        validar_texto(str(v))
    d = ImageDraw.Draw(img)
    d.rectangle([rect.x, rect.y, rect.x + rect.w - 1, rect.y + rect.h - 1], fill=pal["superficie_1"])
    moldura(img, rect, pal)
    pad = max(8, rect.w // 25)
    _texto(img, (rect.x + pad, rect.y + pad - 2), dados.get("CABECALHO", "DOSSIÊ // OP-07"), _fonte("mono", 11), pal["foco"])
    d.line([(rect.x + pad, rect.y + pad + 14), (rect.x + rect.w - pad, rect.y + pad + 14)],
           fill=pal["roxo_profundo"])
    topo = rect.y + pad + 20
    ph = rect.h - (topo - rect.y) - pad - max(14, rect.h // 7) - 6
    pw = int(rect.w * 0.36)
    foto_r = Rect(rect.x + pad, topo, pw, max(ph, 10))
    fonte = foto if foto is not None else placeholder_foto(foto_r, 34)
    img.paste(dither(fonte, foto_r, pal["accent"], pal["fundo"]), (foto_r.x, foto_r.y))
    d.rectangle([foto_r.x, foto_r.y, foto_r.x + foto_r.w - 1, foto_r.y + foto_r.h - 1], outline=pal["foco"])
    x = foto_r.x + pw + pad
    passo = max(14, foto_r.h // len(_CAMPOS))
    fl = _fonte("mono", 9)
    for i, k in enumerate(_CAMPOS):
        y = topo + i * passo
        _texto(img, (x, y), k, fl, _mix(pal["fundo"], pal["texto"], 0.5))
        cor = pal["accent"] if k == "NAME" else pal["texto"]
        valor = str(dados.get(k, "—"))
        tam = max(10, min(18, passo - 6))
        while tam > 8 and _fonte("orbitron", tam).getlength(valor) > rect.x + rect.w - pad - x:
            tam -= 1   # assinatura longa: encolhe até caber no cartão
        _texto(img, (x, y + 9), valor, _fonte("orbitron", tam), cor)
    bh = max(14, rect.h // 7)
    codigo_barras(img, Rect(rect.x + pad, rect.y + rect.h - pad - bh, rect.w // 2, bh), pal, 34)
    _texto(img, (rect.x + rect.w - pad, rect.y + rect.h - pad), dados.get("NAME", "—"), _fonte("dot", 14), pal["accent"], "rd")
