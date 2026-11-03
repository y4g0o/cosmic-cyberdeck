"""Compõe o pôster de cada monitor a partir do layout e da paleta.

Dois estados: com o cyberdeck montado, só aparecem os vãos (molduras, rótulos, trilhas), a faixa do painel
e a zona de arte; sem janelas, aparece o que estava escondido atrás de cada slot.
"""
import math
import random
import time
from pathlib import Path

from PIL import Image, ImageDraw

import marca
from layout import Rect
from poster import modulos as m

FOTOS = {"terminal_livre": "cena", "spotify": "figura", "brave": "olho", "arquivos": "rua"}


# ---------- utilidades ----------
def _foto(fotos_dir: Path | None, nome: str, rect: Rect, seed: int) -> Image.Image:
    if fotos_dir:
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            p = Path(fotos_dir) / f"{nome}{ext}"
            if p.exists():
                return Image.open(p).convert("L")
    return _textura(rect, seed)


def _textura(rect: Rect, seed: int) -> Image.Image:
    """Provisório abstrato (até chegarem as fotos): ruído suave + vinheta + faixas de sinal."""
    import numpy as np
    rng = np.random.default_rng(seed)
    w, h = rect.w, rect.h
    base = Image.fromarray((rng.random((max(2, h // 40), max(2, w // 40))) * 255).astype("uint8"), "L")
    base = np.asarray(base.resize((w, h), Image.BICUBIC), dtype=np.float32)
    fino = np.asarray(Image.fromarray((rng.random((max(2, h // 8), max(2, w // 8))) * 255).astype("uint8"), "L")
                      .resize((w, h), Image.BICUBIC), dtype=np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    vinheta = 1 - np.clip(np.hypot((xx - w / 2) / (w / 1.6), (yy - h / 2) / (h / 1.6)), 0, 1)
    v = (base * 0.65 + fino * 0.35) * (0.35 + 0.65 * vinheta)
    for _ in range(4):  # faixas de interferência
        y0 = int(rng.integers(0, h)); v[y0:y0 + int(rng.integers(2, 8)), :] *= 1.8
    return Image.fromarray(np.clip(v, 0, 255).astype("uint8"), "L")


def _colar_dither(img, fonte: Image.Image, rect: Rect, cor: str, pal: dict, centro=(0.5, 0.3)):
    img.paste(m.dither(fonte, rect, cor, pal["fundo"], centro), (rect.x, rect.y))


def _sub(r: Rect, fx: float, fy: float, fw: float, fh: float) -> Rect:
    return Rect(r.x + round(r.w * fx), r.y + round(r.h * fy), max(8, round(r.w * fw)), max(8, round(r.h * fh)))


def _grade(img, pal):
    d = ImageDraw.Draw(img)
    cor = m._mix(pal["fundo"], pal["roxo_profundo"], 0.35)
    for x in range(0, img.width, 40):
        d.line([x, 0, x, img.height], fill=cor)
    for y in range(0, img.height, 40):
        d.line([0, y, img.width, y], fill=cor)


def _faixa_painel(img, pal, painel: int):
    """Moldura de HUD nos 32 px do topo (o painel do COSMIC é translúcido)."""
    d = ImageDraw.Draw(img)
    w = img.width
    d.rectangle([0, 0, w, painel], fill=pal["fundo_2"])
    hach = m._mix(pal["fundo_2"], pal["foco"], 0.12)
    for x in range(-painel, w, 7):
        d.line([x, painel, x + painel, 0], fill=hach)
    y = painel - 3
    esq = int(w * 0.16)
    d.rectangle([0, y, esq, y + 2], fill=pal["accent"])
    d.polygon([(esq, y), (esq + 10, y - 6), (esq + 10, y - 4), (esq + 2, y + 2)], fill=pal["accent"])
    d.line([esq + 10, y - 5, int(w * 0.40), y - 5], fill=m._mix(pal["fundo_2"], pal["accent"], 0.5))
    d.line([esq + 4, y + 1, int(w * 0.9), y + 1], fill=m._mix(pal["fundo_2"], pal["foco"], 0.5))
    c, lado = w // 2, 150
    for sx in (-1, 1):
        x = c + sx * lado
        d.line([x, y - 6, x, y + 2], fill=pal["accent"], width=2)
        d.line([x, y + 2, x - sx * 40, y + 2], fill=pal["accent"], width=2)
    dr = int(w * 0.9)
    d.rectangle([dr, y, w, y + 2], fill=pal["alerta"])
    for i in range(6):
        x = dr - 14 - i * 9
        d.line([x, y - 3, x, y + 1], fill=pal["alerta"], width=2)
    m.texto(img, (int(w * 0.20), 9), "NET.LINK [####-]  //  NODE 07", m._mix(pal["fundo_2"], pal["foco"], 0.6), "mono", 12)
    m.texto(img, (c + lado + 30, 9), "SYS.SYNC  0x7F3A", m._mix(pal["fundo_2"], pal["accent"], 0.6), "mono", 12)


def _moldura_do_slot(img, r: Rect, pal: dict, gap: int):
    """Desenha no vão em volta do slot: moldura chanfrada a gap/2."""
    off = gap // 2 - 1
    m.moldura(img, Rect(r.x - off, r.y - off, r.w + 2 * off, r.h + 2 * off), pal, chanfro=14)


def _trilha(d, pts, cor, pal, largura=2):
    d.line(pts, fill=cor, width=largura)
    for px, py in (pts[0], pts[-1]):
        d.ellipse([px - 4, py - 4, px + 4, py + 4], outline=cor, fill=pal["fundo"], width=2)


# ---------- conteúdo escondido atrás de cada slot ----------
def _atras_spotify(img, r, pal, fotos, seed):
    foto = _sub(r, 0.02, 0.04, 0.96, 0.56)
    _colar_dither(img, _foto(fotos, "cena", foto, seed), foto, pal["accent"], pal)
    m.moldura(img, foto, pal)
    m.titulo(img, (r.x + round(r.w * 0.03), r.y + round(r.h * 0.64)), "TORRE DE SINAL // 07", pal, 40)
    m.texto(img, (r.x + round(r.w * 0.03), r.y + round(r.h * 0.73)), "transmissão em curso · 接続確立 · signal locked", pal["foco"], "mono", 16)
    m.codigo_barras(img, _sub(r, 0.60, 0.64, 0.37, 0.10), pal, seed)
    m.microtexto(img, _sub(r, 0.03, 0.80, 0.94, 0.16), pal, seed)


def _tem_foto(fotos, nome):
    return bool(fotos) and any((Path(fotos) / f"{nome}{e}").exists() for e in (".png", ".jpg", ".jpeg", ".webp"))


def _atras_cava(img, r, pal, fotos, seed):
    if _tem_foto(fotos, "viaduto"):   # faixa larga: panorama de ponta a ponta, texto embaixo
        foto = _sub(r, 0.02, 0.05, 0.96, 0.62)
        _colar_dither(img, _foto(fotos, "viaduto", foto, seed), foto, pal["foco"], pal, centro=(0.5, 0.5))
        m.moldura(img, foto, pal)
        m.texto(img, (r.x + 24, r.y + round(r.h * 0.72)), "信号解析 // SPECTRUM", pal["accent"], "cjk", 26)
        m.codigo_barras(img, _sub(r, 0.52, 0.72, 0.44, 0.12), pal, seed + 1)
        m.microtexto(img, _sub(r, 0.02, 0.88, 0.96, 0.10), pal, seed + 2)
        return
    m.onda(img, _sub(r, 0.02, 0.08, 0.96, 0.46), pal, seed)
    m.texto(img, (r.x + 24, r.y + round(r.h * 0.58)), "信号解析 // SPECTRUM", pal["accent"], "cjk", 26)
    m.codigo_barras(img, _sub(r, 0.04, 0.70, 0.56, 0.12), pal, seed + 1)
    m.microtexto(img, _sub(r, 0.02, 0.86, 0.96, 0.12), pal, seed + 2)


def _atras_terminal_livre(img, r, pal, fotos, seed):
    ficha = {"NAME": marca.assinatura(), "FUNCTION": "NETRUNNER", "STATE": "ONLINE", "CLEARANCE": "LVL 07", "LOCATION": "SETOR 07"}
    if r.w > r.h * 1.3:   # espaço largo: ficha e texto à esquerda, figura em pé à direita
        m.ficha_operador(img, _sub(r, 0.03, 0.05, 0.52, 0.52), pal, ficha)
        m.titulo(img, (r.x + round(r.w * 0.03), r.y + round(r.h * 0.64)), "OPERADOR // ATIVO", pal, 34)
        m.texto(img, (r.x + round(r.w * 0.03), r.y + round(r.h * 0.74)), "identidade verificada · 認証済み", pal["foco"], "cjk", 16)
        m.microtexto(img, _sub(r, 0.03, 0.81, 0.52, 0.15), pal, seed)
        foto = _sub(r, 0.59, 0.05, 0.38, 0.90)
    else:
        m.ficha_operador(img, _sub(r, 0.04, 0.03, 0.92, 0.42), pal, ficha)
        foto = _sub(r, 0.04, 0.50, 0.92, 0.46)
    _colar_dither(img, _foto(fotos, "figura", foto, seed), foto, pal["foco"], pal)
    m.moldura(img, foto, pal)


def _atras_brave(img, r, pal, fotos, seed):
    foto = _sub(r, 0.03, 0.04, 0.94, 0.56)
    _colar_dither(img, _foto(fotos, "olho", foto, seed), foto, pal["foco"], pal)
    m.moldura(img, foto, pal)
    m.titulo(img, (r.x + round(r.w * 0.03), r.y + round(r.h * 0.63)), "VISUAL FEED", pal, 44)
    m.texto(img, (r.x + round(r.w * 0.03), r.y + round(r.h * 0.70)), "監視中 // RECORDING  ·  OPTIC.07", pal["accent"], "cjk", 20)
    m.codigo_barras(img, _sub(r, 0.60, 0.63, 0.37, 0.09), pal, seed + 1)
    m.onda(img, _sub(r, 0.03, 0.75, 0.94, 0.10), pal, seed)
    m.microtexto(img, _sub(r, 0.03, 0.87, 0.94, 0.10), pal, seed + 2)


def _atras_terminal_rapido(img, r, pal, fotos, seed):
    if _tem_foto(fotos, "mao"):   # foto à esquerda, leitura de dados à direita
        foto = _sub(r, 0.03, 0.05, 0.56, 0.90)
        _colar_dither(img, _foto(fotos, "mao", foto, seed), foto, pal["accent"], pal, centro=(0.5, 0.5))
        m.moldura(img, foto, pal)
        x = foto.x + foto.w + round(r.w * 0.03)
        larg = r.x + r.w - x - round(r.w * 0.03)
        m.texto(img, (x, r.y + round(r.h * 0.08)), "生体接続", pal["accent"], "cjk", 28)
        m.texto(img, (x, r.y + round(r.h * 0.18)), "BIO.LINK // SYNC", pal["foco"], "mono", 16)
        m.onda(img, Rect(x, r.y + round(r.h * 0.28), larg, round(r.h * 0.24)), pal, seed + 3)
        m.codigo_barras(img, Rect(x, r.y + round(r.h * 0.58), larg, round(r.h * 0.14)), pal, seed + 4)
        m.microtexto(img, Rect(x, r.y + round(r.h * 0.76), larg, round(r.h * 0.19)), pal, seed)
        return
    m.microtexto(img, _sub(r, 0.03, 0.05, 0.60, 0.88), pal, seed)
    m.onda(img, _sub(r, 0.66, 0.08, 0.31, 0.40), pal, seed + 3)
    m.codigo_barras(img, _sub(r, 0.66, 0.58, 0.31, 0.30), pal, seed + 4)


def _atras_arquivos(img, r, pal, fotos, seed):
    # foto quadrada: quadro pouco mais largo que alto e recorte mirando embaixo, onde fica o carro
    foto = _sub(r, 0.03, 0.06, 0.62, 0.88) if r.w > r.h * 1.3 else _sub(r, 0.03, 0.06, 0.94, 0.70)
    _colar_dither(img, _foto(fotos, "rua", foto, seed), foto, pal["accent"], pal, centro=(0.5, 0.85))
    m.moldura(img, foto, pal)
    if r.w > r.h * 1.3:   # texto na coluna ao lado da foto
        x = foto.x + foto.w + round(r.w * 0.03)
        m.texto(img, (x, r.y + round(r.h * 0.10)), "ARQUIVO MORTO", pal["foco"], "mono", 22)
        m.texto(img, (x, r.y + round(r.h * 0.18)), "記録保管", pal["accent"], "cjk", 26)
        m.codigo_barras(img, Rect(x, r.y + round(r.h * 0.32), r.x + r.w - x - round(r.w * 0.03), round(r.h * 0.16)), pal, seed)
        m.microtexto(img, Rect(x, r.y + round(r.h * 0.54), r.x + r.w - x - round(r.w * 0.03), round(r.h * 0.40)), pal, seed + 1)
    else:
        m.texto(img, (r.x + round(r.w * 0.04), r.y + round(r.h * 0.82)), "ARQUIVO MORTO // 記録保管", pal["foco"], "cjk", 26)


ATRAS = {  # o que fica escondido atrás de cada slot (a função leva o nome do conteúdo, não do app)
    "terminal_livre": _atras_spotify, "spotify": _atras_terminal_livre, "cava": _atras_cava,
    "brave": _atras_brave, "hud": _atras_terminal_rapido, "arquivos": _atras_arquivos,
}


# ---------- zona de arte (sempre visível) ----------
def _emblema(d, cx, cy, raio, pal):
    hexa = [(cx + raio * math.cos(math.radians(60 * i + 30)), cy + raio * math.sin(math.radians(60 * i + 30))) for i in range(6)]
    d.polygon(hexa, outline=pal["accent"], width=4)
    ri = raio * 0.55
    d.polygon([(cx, cy - ri), (cx + ri * 0.87, cy + ri * 0.5), (cx - ri * 0.87, cy + ri * 0.5)], outline=pal["texto"], width=3)
    d.ellipse([cx - raio * 0.12, cy - raio * 0.04, cx + raio * 0.12, cy + raio * 0.2], fill=pal["foco"])


def _zona_arte(img, r: Rect, pal, seed):
    d = ImageDraw.Draw(img)
    faixa = Rect(r.x + r.w - 96, r.y, 84, r.h)
    d.rectangle([faixa.x, faixa.y, faixa.x + faixa.w, faixa.y + faixa.h], fill=pal["accent"])
    m.texto_vertical(img, (faixa.x + 12, faixa.y + 24), "企業安全保障局", pal["fundo"], "dela", 58)
    m.texto_vertical(img, (faixa.x - 34, faixa.y + 40), "監視ネットワーク稼働中", pal["muted"], "dot", 22)
    _emblema(d, r.x + round(r.w * 0.40), r.y + round(r.h * 0.22), round(r.w * 0.20), pal)
    nome, tam = marca.assinatura(), 118
    while tam > 40 and m._fonte("orbitron", tam).getlength(nome) > r.w - 140:
        tam -= 4   # assinatura longa: encolhe até caber antes da faixa vertical
    m.titulo(img, (r.x + 24, r.y + round(r.h * 0.44)), nome, pal, tam)
    d.rectangle([r.x + 26, r.y + round(r.h * 0.57), r.x + round(r.w * 0.62), r.y + round(r.h * 0.57) + 5], fill=pal["accent"])
    m.texto(img, (r.x + 26, r.y + round(r.h * 0.60)), "オペレーター // ОПЕРАТОР // 운영자", pal["muted"], "cjk", 18)
    rnd = random.Random(seed)
    linhas = ["TRACE ROUTE  経路追跡"] + [f"{i:02d}  10.{rnd.randint(0,255)}.{rnd.randint(0,255)}.{rnd.randint(1,254)}  {rnd.randint(2,90):>3} ms" for i in range(1, 6)]
    for i, ln in enumerate(linhas):
        cor = pal["alerta"] if i == len(linhas) - 1 else (pal["foco"] if i == 0 else pal["texto_4"])
        m.texto(img, (r.x + 26, r.y + round(r.h * 0.67) + i * 22), ln, cor, "mono", 16)
    m.texto(img, (r.x + 26, r.y + round(r.h * 0.67) + 6 * 22 + 8), "СОЕДИНЕНИЕ УСТАНОВЛЕНО", pal["foco"], "cjk", 16)
    m.titulo(img, (r.x + 26, r.y + r.h - 46), "SIGNAL ACQUIRED", pal, 26)


# ---------- trilhas ----------
def _trilhas(img, saida: str, L, pal, seed):
    d = ImageDraw.Draw(img)
    rnd = random.Random(seed)
    slots = {**L.slots(saida), **L.zonas(saida)}
    w, h = img.size
    g = L.gap_interno
    cores = [pal["circuito"], pal["foco"], pal["accent"]]
    arte = L.zonas(saida).get("arte")
    if arte:   # trilhas internas: dos vãos até o emblema da zona de arte (monitores isolados)
        alvo = (arte.x + round(arte.w * 0.40), arte.y + round(arte.h * 0.22))
        for i, y in enumerate((arte.y + 120, arte.y + 380, arte.y + 640)):
            x0 = arte.x - g // 2
            _trilha(d, [(x0, y), (x0 + 30 + i * 12, y), (x0 + 30 + i * 12, y + (alvo[1] - y) // 3), alvo], cores[i % 3], pal)
    # trilhas pelos vãos entre slots (horizontais e verticais)
    for a in slots.values():
        for b in slots.values():
            if b.x > a.x + a.w and abs(b.y - a.y) < 8:   # b à direita de a
                xm = a.x + a.w + g // 2
                for k in range(2):
                    y0 = a.y + rnd.randint(40, max(41, a.h - 40))
                    _trilha(d, [(xm, y0), (xm, y0 + rnd.randint(-120, 120))], cores[(k + 1) % 3], pal, 2)
            if b.y > a.y + a.h and abs(b.x - a.x) < 8:   # b abaixo de a
                ym = a.y + a.h + g // 2
                x0 = a.x + rnd.randint(40, max(41, a.w - 40))
                _trilha(d, [(x0, ym), (x0 + rnd.randint(-200, 200), ym)], cores[2], pal, 2)


# ---------- API ----------
def compor(saida: str, L, pal: dict, fotos_dir: Path | None) -> Image.Image:
    w, h = L.tamanho(saida)
    img = Image.new("RGB", (w, h), pal["fundo"])
    seed = sum(map(ord, saida))
    _grade(img, pal)
    for i, (nome, r) in enumerate(L.slots(saida).items()):
        ATRAS[nome](img, r, pal, fotos_dir, seed + i)
    for nome, r in L.zonas(saida).items():
        _zona_arte(img, r, pal, seed)
    for r in {**L.slots(saida), **L.zonas(saida)}.values():
        _moldura_do_slot(img, r, pal, L.gap_interno)
    _trilhas(img, saida, L, pal, seed)
    _faixa_painel(img, pal, L.painel)
    return img


def gerar(saidas: list[str], L, pal: dict, fotos_dir: Path | None, out_dir: Path):
    """Gera os pôsteres das saídas pedidas que existem no layout. Retorna [(saida, caminho)]."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    versao = time.strftime("%Y%m%d-%H%M%S")
    feitas = []
    for s in saidas:
        if s not in L.saidas():
            continue
        caminho = out_dir / f"poster-{s}-v{versao}.png"
        compor(s, L, pal, fotos_dir).save(caminho)
        feitas.append((s, caminho))
    return feitas


def limpar_antigos(out_dir: Path, manter: set[Path]):
    """Apaga pôsteres antigos, nunca os que alguma config ainda usa."""
    manter = {Path(p).resolve() for p in manter}
    for p in Path(out_dir).glob("poster-*-v*.png"):
        if p.resolve() not in manter:
            p.unlink()
