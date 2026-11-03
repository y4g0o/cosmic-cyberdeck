"""Placas do cyberdeck no tema de ícones: apps dentro de uma placa chanfrada com borda neon e pastas desenhadas.

Roda sobre o Papirus-cyberdeck já recolorido (gerar_icones.py chama no fim). Ícones abaixo de 32 px ficam como
estão (a placa deixaria o símbolo ilegível); pastas pequenas ganham só o traço com o símbolo. O código de arquivo
das pastas grandes ("01 // DOC") vai como PNG embutido: as letras não dependem de fonte instalada no renderizador.
Uso: python3 gerar_placas.py   (aplica no ~/.local/share/icons/Papirus-cyberdeck)
"""
import base64
import io
import re
import sys
from pathlib import Path

from PIL import Image

import paleta
from poster import modulos

MARCA = "<!-- cyberdeck-placa -->"
DESTINO = Path.home() / ".local/share/icons/Papirus-cyberdeck"
MIN_PLACA = 32
PLACA = "10,1.5 62.5,1.5 62.5,54 54,62.5 1.5,62.5 1.5,10"   # cantos superior-esquerdo e inferior-direito cortados

# símbolos dentro do corpo da pasta (caixa de 64 unidades; corpo entre y 27 e 52)
SIMBOLOS = {
    "pasta": "",
    "documents": "M26 31H35L39 35V48H26Z M35 31V35H39 M29 40H36 M29 44H36",
    "download": "M32 30V43 M26 38L32 44L38 38 M25 48H39",
    "music": "M30 45V32L40 30V43 M26 43h4v4h-4z M36 41h4v4h-4z",
    "pictures": "M24 31H40V47H24Z M24 44L30 37L34 41L37 38L40 41",
    "videos": "M28 31L39 39L28 47Z",
    "home": "M24 40L32 32L40 40 M26 38V47H38V38 M30 47V42H34V47",
    "desktop": "M23 31H41V43H23Z M28 48H36 M32 43V48",
    "templates": "M25 32H39 M25 37H39 M25 42H34 M25 47H37",
    "share": "M27 39L37 33 M27 39L37 45 M24 37h5v5h-5z M35 31h5v5h-5z M35 43h5v5h-5z",
}
PASTAS = {   # nome do ícone -> (símbolo, código de arquivo); estilo "etiqueta de arquivo", sem kanji
    "folder": ("pasta", "// DIR"), "inode-directory": ("pasta", "// DIR"),
    "folder-home": ("home", "00 // HOME"), "user-home": ("home", "00 // HOME"),
    "folder-documents": ("documents", "01 // DOC"), "folder-download": ("download", "02 // DL"),
    "folder-music": ("music", "03 // AUDIO"), "folder-pictures": ("pictures", "04 // IMG"),
    "folder-videos": ("videos", "05 // VID"),
    "folder-desktop": ("desktop", "06 // DESK"), "user-desktop": ("desktop", "06 // DESK"),
    "folder-templates": ("templates", "07 // TMPL"), "folder-publicshare": ("share", "08 // PUB"),
}
PASTA = "M6 16H24L29 21H58V52H6Z M6 27H58"

# Ícones simbólicos da barra lateral (caixa 16x16, traço angular chanfrado): (categoria, principal, detalhe)
_SIMB_FORMAS = {
    "pasta": ("M1.5 3H6L7.5 4.5H14.5V12L13 13.5H1.5Z", "M1.5 6.5H14.5 M11.5 2H14.5V5"),
    "home": ("M1.5 7.5L8 1.5L14.5 7.5 M3 6.5V14.5H13V6.5", "M6.5 14.5V10H9.5V14.5 M7 5.5H9"),
    "desktop": ("M1.5 2.5H12.5L14.5 4.5V11.5H1.5Z M5 14.5H11 M8 11.5V14.5", "M3.5 5H7 M3.5 7.5H5.5"),
    "documents": ("M2.5 1.5H10.5L13.5 4.5V14.5H2.5Z", "M10 1.5V5H13.5 M5 8H11 M5 11H9.5"),
    "download": ("M8 1.5V10.5 M4.5 7L8 10.5L11.5 7", "M2 11.5L3.5 14.5H12.5L14 11.5"),
    "music": ("M5.5 12.5V3.5L13.5 2V11 M2.5 11H5.5V14H2.5Z M10.5 9.5H13.5V12.5H10.5Z", "M5.5 6.5L13.5 5"),
    "pictures": ("M1.5 2.5H12.5L14.5 4.5V13.5H1.5Z", "M1.5 11.5L5.5 7.5L8.5 10.5L11 8L14.5 11.5 M10.5 5H12V6.5H10.5Z"),
    "videos": ("M1.5 2.5H12.5L14.5 4.5V13.5H1.5Z", "M6 5.5L11 8L6 10.5Z"),
    "templates": ("M2.5 1.5H10.5L13.5 4.5V14.5H2.5Z", "M5 6H11 M5 9H11 M5 12H8.5"),
    "share": ("M2 6.5H5V9.5H2Z M11 2.5H14V5.5H11Z M11 10.5H14V13.5H11Z", "M5 8L11 4 M5 8L11 12"),
    "recent": ("M5 1.5H11L14.5 5V11L11 14.5H5L1.5 11V5Z", "M8 4.5V8.5L11 10.5"),
    "trash": ("M1.5 3.5H14.5 M3 3.5V12.5L4.5 14.5H11.5L13 12.5V3.5", "M5.5 3.5V1.5H10.5V3.5 M6.5 6.5V11.5 M9.5 6.5V11.5"),
    "trash_full": ("M1.5 3.5H14.5 M3 3.5V12.5L4.5 14.5H11.5L13 12.5V3.5", "M5.5 3.5V1.5H10.5V3.5 M5 6.5H11 M6.5 6.5V11.5 M9.5 6.5V11.5"),
    "network": ("M2 2.5H14V6.5H2Z M2 9.5H14V13.5H2Z", "M4.5 4.5H6.5 M4.5 11.5H6.5 M8 6.5V9.5"),
    "bookmark": ("M3.5 1.5H11L12.5 3V14.5L8 11L3.5 14.5Z", "M6 5H10"),
    "drive": ("M2.5 1.5H11.5L13.5 3.5V14.5H2.5Z M2.5 10.5H13.5", "M5.5 4.5H10.5V7.5H5.5Z M5 12.5H7 M10.5 12.5H11.5"),
}
SIMBOLICOS = {
    "folder-symbolic": ("places", "pasta"), "inode-directory-symbolic": ("places", "pasta"),
    "user-home-symbolic": ("places", "home"), "folder-home-symbolic": ("places", "home"),
    "user-desktop-symbolic": ("places", "desktop"), "folder-desktop-symbolic": ("places", "desktop"),
    "folder-documents-symbolic": ("places", "documents"), "folder-download-symbolic": ("places", "download"),
    "folder-music-symbolic": ("places", "music"), "folder-pictures-symbolic": ("places", "pictures"),
    "folder-videos-symbolic": ("places", "videos"), "folder-templates-symbolic": ("places", "templates"),
    "folder-publicshare-symbolic": ("places", "share"), "folder-recent-symbolic": ("places", "recent"),
    "user-trash-symbolic": ("places", "trash"), "user-trash-full-symbolic": ("places", "trash_full"),
    "network-workgroup-symbolic": ("places", "network"), "network-server-symbolic": ("places", "network"),
    "folder-remote-symbolic": ("places", "network"),
    "user-bookmarks-symbolic": ("places", "bookmark"), "starred-symbolic": ("places", "bookmark"),
    "document-open-recent-symbolic": ("actions", "recent"),
    "drive-harddisk-symbolic": ("devices", "drive"), "drive-harddisk-system-symbolic": ("devices", "drive"),
    "drive-harddisk-solidstate-symbolic": ("devices", "drive"), "drive-harddisk-usb-symbolic": ("devices", "drive"),
    "drive-removable-media-symbolic": ("devices", "drive"), "drive-multidisk-symbolic": ("devices", "drive"),
}


def _cantos(cor):
    return f'<rect x="56.5" y="3" width="4" height="4" fill="{cor}"/><rect x="3" y="57" width="4" height="4" fill="{cor}"/>'


def _placa(pal, borda):
    return (f'<polygon points="{PLACA}" fill="{pal["superficie_1"]}" stroke="{borda}" stroke-width="1.6" '
            f'stroke-linejoin="miter"/>' + _cantos(pal["accent"]))


def _n(v: float) -> str:
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def em_placa(svg: str, pal: dict) -> str | None:
    """O ícone de app dentro da placa (borda verde-ácido). None se já tem placa ou não dá para medir."""
    if MARCA in svg:
        return None
    raiz = re.search(r"<svg\b[^>]*>", svg)
    fim = svg.rfind("</svg>")
    if not raiz or fim < raiz.end():
        return None
    tag = raiz.group(0)
    vb = re.search(r'viewBox="([^"]+)"', tag)
    w, h = (re.search(rf'(?<![\w-]){a}="([\d.]+)(?:px)?"', tag) for a in ("width", "height"))
    if vb:
        x0, y0, cw, ch = (float(v) for v in vb.group(1).replace(",", " ").split())
    elif w and h:
        x0, y0, cw, ch = 0.0, 0.0, float(w.group(1)), float(h.group(1))
    else:
        return None
    if cw <= 0 or ch <= 0:
        return None
    k = 48 / max(cw, ch)   # cabe em 48x48, centrado (8 de margem) dentro da caixa de 64 da placa
    dx, dy = 8 + (48 - cw * k) / 2, 8 + (48 - ch * k) / 2
    ns = " ".join(re.findall(r'xmlns:\w+="[^"]*"', tag))
    herda = " ".join(re.findall(r'(?<![\w-])(?:style|fill|stroke|color|opacity|fill-rule)="[^"]*"', tag))   # da raiz: vai para o grupo
    tam = f'width="{w.group(1)}" height="{h.group(1)}"' if w and h else 'width="64" height="64"'
    dentro = svg[raiz.end():fim]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" {ns} {tam} viewBox="0 0 64 64">{MARCA}'
            f'{_placa(pal, pal["accent"])}'
            f'<g transform="translate({_n(dx)} {_n(dy)}) scale({_n(k)}) translate({_n(-x0)} {_n(-y0)})" {herda}>'
            f'{dentro}</g></svg>\n')


FOLHAS_PAPIRUS = (   # a mesma folha, escrita de duas formas nos arquivos do Papirus
    "M 12.75,4 C 11.2265,4 10,5.2488 10,6.8 v 50.4 c 0,1.55008 1.2265,2.8 2.75,2.8 h 38.5 "
    "C 52.7724,60 54,58.75008 54,57.2 V 22 L 40,18 36,4 Z",
    "m12.75 4c-1.5235 0-2.75 1.2488-2.75 2.8v50.4c0 1.55008 1.2265 2.8 2.75 2.8h38.5c1.5224 0 2.75-1.24992 "
    "2.75-2.8v-35.2l-14-4-4-14z",
)
FOLHA_PAPIRUS = FOLHAS_PAPIRUS[0]
_SOBRAS_DA_FOLHA = ("M 12.75,5 C", "M 54,23 36,5", "M 54,22 36,4", "M 12.75 4 C 11.2265 4 10 5.2495812",
                    "m12.75 5c", "m54 23-18-18", "m54 22-18-18", "m12.75 4c-1.5235 0-2.75 1.2495812")


def _clarear(corpo: str, clara: str) -> str:
    """Cores escuras e sem saturação (feitas para a folha clara) viram a cor clara do tema."""
    def troca(m):
        r, g, b = (int(m.group(2)[i:i + 2], 16) / 255 for i in (1, 3, 5))
        escura = 0.2126 * r + 0.7152 * g + 0.0722 * b < 0.35 and not _saturada(m.group(2))
        return f"{m.group(1)}{clara}" if escura else m.group(0)
    return re.sub(r'((?:fill|stroke)(?::|=")\s*)(#[0-9a-fA-F]{6})\b', troca, corpo)


def _saturada(hexcor: str) -> bool:
    r, g, b = (int(hexcor[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return max(r, g, b) - min(r, g, b) > 0.25


def em_ficha(svg: str, pal: dict) -> str | None:
    """Tipo de arquivo: a folha clara do Papirus vira ficha escura chanfrada com borda neon; o símbolo do tipo
    fica, e o que era escuro sobre a folha clara (linhas de texto) passa a ser claro. None se não é a folha."""
    forma = next((f for f in FOLHAS_PAPIRUS if f in svg), None)
    if MARCA in svg or forma is None:
        return None
    raiz = re.search(r"<svg\b[^>]*>", svg)
    fim = svg.rfind("</svg>")
    corpo = svg[raiz.end():fim]
    folha = re.search(r'<path\b[^>]*d="' + re.escape(forma) + r'"[^>]*/>', corpo)
    cor = re.search(r"fill:(#[0-9a-fA-F]{6})", folha.group(0))
    borda = cor.group(1) if cor and _saturada(cor.group(1)) else pal["foco"]
    corpo = corpo.replace(folha.group(0), "")
    for sobra in _SOBRAS_DA_FOLHA:
        corpo = re.sub(r'<path\b[^>]*d="' + re.escape(sobra) + r'[^"]*"[^>]*/>', "", corpo)
    ficha = (f'<path d="M10 4H43L54 15V60H10Z" fill="{pal["superficie_1"]}" stroke="{borda}" stroke-width="1.6" '
             f'stroke-linejoin="miter"/><path d="M43 4V15H54" fill="none" stroke="{borda}" stroke-width="1.2"/>'
             f'<rect x="12" y="55" width="3" height="3" fill="{pal["accent"]}"/>')
    return f'{raiz.group(0)}{MARCA}{ficha}<g fill="{pal["texto"]}">{_clarear(corpo, pal["texto"])}</g></svg>\n'


def _rotulo_png(texto: str, cor: str) -> str:
    """Código de arquivo em PNG (base64), fonte mono, alinhado à esquerda, 4x a área que ocupa no ícone."""
    img = Image.new("RGBA", (192, 36), (0, 0, 0, 0))
    modulos.texto(img, (2, 18), texto, cor, "mono", 30, ancora="lm")
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def pasta(nome: str, tam: int, pal: dict) -> str:
    simbolo, codigo = PASTAS[nome]
    traco = f'stroke="{pal["accent"]}" fill="none" stroke-linejoin="miter"'
    desenho = (f'<path d="{PASTA}" {traco} stroke-width="3.2"/>'
               + (f'<path d="{SIMBOLOS[simbolo]}" {traco} stroke-width="2.6"/>' if SIMBOLOS[simbolo] else ""))
    if tam < MIN_PLACA:
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{tam}" height="{tam}" viewBox="0 0 64 64">{desenho}</svg>\n'
    if tam >= 48:   # pasta no alto; filete e código de arquivo embaixo
        miolo = f'<g transform="translate(12 5) scale(0.625)">{desenho}</g>'
        miolo += (f'<path d="M7 46.5H57" stroke="{pal["roxo_profundo"]}" stroke-width="0.8"/>'
                  f'<image x="8" y="48.5" width="48" height="9" '
                  f'href="data:image/png;base64,{_rotulo_png(codigo, pal["muted"])}"/>')
    else:
        miolo = f'<g transform="translate(8 6) scale(0.75)">{desenho}</g>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{tam}" height="{tam}" viewBox="0 0 64 64">{MARCA}'
            f'{_placa(pal, pal["foco"])}{miolo}</svg>\n')


def simbolico(nome: str, tam: int, pal: dict) -> str:
    _, forma = SIMBOLICOS[nome]
    p1, p2 = _SIMB_FORMAS[forma]
    est = 'fill="none" stroke-linejoin="miter" stroke-linecap="square"'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{tam}" height="{tam}" viewBox="0 0 16 16">{MARCA}'
            f'<path d="{p2}" stroke="{pal["foco"]}" stroke-width="1.3" {est}/>'
            f'<path d="{p1}" stroke="{pal["accent"]}" stroke-width="1.5" {est}/></svg>\n')


def _tamanho(pasta_tam: Path) -> int | None:
    m = re.match(r"(\d+)x\d+(@2x)?$", pasta_tam.name)   # tamanho lógico: o @2x é só mais nítido, não maior
    return int(m.group(1)) if m else None


def aplicar(destino: Path, pal: dict) -> tuple[int, int, int]:
    apps = pastas = fichas = 0
    for d in sorted(destino.iterdir()):
        tam = _tamanho(d)
        if tam is None or d.is_symlink() or not d.is_dir():
            continue
        if tam >= MIN_PLACA and (d / "apps").is_dir() and not (d / "apps").is_symlink():
            for f in (d / "apps").glob("*.svg"):
                if f.is_symlink():
                    continue   # links apontam para arquivos que também recebem placa
                novo = em_placa(f.read_text(errors="ignore"), pal)
                if novo:
                    f.write_text(novo)
                    apps += 1
        tipos = d / "mimetypes"
        if tam >= MIN_PLACA and tipos.is_dir() and not tipos.is_symlink():
            for f in tipos.glob("*.svg"):
                if f.is_symlink():
                    continue
                novo = em_ficha(f.read_text(errors="ignore"), pal)
                if novo:
                    f.write_text(novo)
                    fichas += 1
        lugar = d / "places"
        if lugar.is_dir() and not lugar.is_symlink():
            for nome in PASTAS:
                alvo = lugar / f"{nome}.svg"
                if alvo.is_symlink():
                    alvo.unlink()
                alvo.write_text(pasta(nome, tam, pal))
                pastas += 1
        for prefixo in ("", "symbolic/", "symbolic-up-to-20/"):
            for nome, (cat, _) in SIMBOLICOS.items():
                pasta_cat = d / f"{prefixo}{cat}"
                if pasta_cat.is_dir() and not pasta_cat.is_symlink():
                    alvo = pasta_cat / f"{nome}.svg"
                    if prefixo or alvo.exists() or alvo.is_symlink():
                        if alvo.is_symlink():
                            alvo.unlink()
                        alvo.write_text(simbolico(nome, tam, pal))
                        pastas += 1
    return apps, pastas, fichas


if __name__ == "__main__":
    apps, pastas, fichas = aplicar(DESTINO, paleta.carregar())
    print(f"placas: {apps} ícones de app, {pastas} pastas, {fichas} tipos de arquivo")
    sys.exit(0)
