"""Gera o tema de ícones 'Papirus-cyberdeck': Papirus recolorido em duotone neon com a paleta ativa."""
import colorsys
import pathlib
import re
import shutil
import sys

import paleta

ICONS = pathlib.Path.home() / ".local/share/icons"


def origem(nome):
    """Tema base (Papirus/Papirus-Dark): o do usuário se existir, senão o do pacote papirus-icon-theme."""
    for d in (ICONS, pathlib.Path("/usr/share/icons")):
        if (d / nome).is_dir():
            return d / nome
    raise SystemExit(f"{nome} não encontrado: instale o pacote papirus-icon-theme")


# (escuro, neon, claro) por família de cor
def _mix(a, b, t):
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(paleta.hex_rgb(a), paleta.hex_rgb(b)))


def rampas(pal):
    """(escuro, neon, claro) por família de cor de origem, derivado da paleta ativa."""
    r = {}
    for familia, chave in (("ciano", "foco"), ("vermelho", "alerta"), ("amarelo", "accent"), ("rosa", "rosa")):
        neon = pal[chave]
        r[familia] = (_mix(pal["fundo"], neon, 0.18), neon, _mix(neon, "#FFFFFF", 0.8))
    r["aco"] = (pal["sup_a"], pal["fraco"], pal["texto_2"])
    return r


RAMPAS = rampas(paleta.carregar())
HEX = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def mapear(cor):
    if len(cor) == 3:
        cor = "".join(c * 2 for c in cor)
    r, g, b = rgb(cor)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    if s < 0.18 or l < 0.06:
        familia = "aco"
    elif 0.10 <= h < 0.45:  # amarelos e verdes
        familia = "amarelo"
    elif 0.45 <= h < 0.75:  # verde-azulados e azuis
        familia = "ciano"
    elif 0.75 <= h < 0.92:
        familia = "rosa"
    else:
        familia = "vermelho"
    escuro, neon, claro = (rgb(x) for x in RAMPAS[familia])
    novo = lerp(escuro, neon, l / 0.5) if l < 0.5 else lerp(neon, claro, (l - 0.5) / 0.5)
    return "#%02x%02x%02x" % tuple(round(c * 255) for c in novo)


def recolorir(origem, destino, nome, herda):
    if destino.exists():
        shutil.rmtree(destino)
    shutil.copytree(origem, destino, symlinks=True)
    for link in destino.rglob("*"):  # Papirus-Dark aponta pastas para ../Papirus/ em vários níveis
        if link.is_symlink() and "/Papirus/" in str(link.readlink()):
            alvo = str(link.readlink()).replace("/Papirus/", "/Papirus-cyberdeck/")
            link.unlink()
            link.symlink_to(alvo)
    n = 0
    for svg in destino.rglob("*.svg"):
        if svg.is_symlink() or not svg.is_file():
            continue
        t = svg.read_text(errors="ignore")
        novo = HEX.sub(lambda m: mapear(m.group(1)), t)
        if novo != t:
            svg.write_text(novo)
            n += 1
    idx = destino / "index.theme"
    txt = idx.read_text()
    txt = re.sub(r"(?m)^Name=.*$", f"Name={nome}", txt)
    txt = re.sub(r"(?m)^Inherits=.*$", f"Inherits={herda}", txt)
    idx.write_text(txt)
    for cache in destino.glob("icon-theme.cache"):
        cache.unlink()
    print(nome, n, "svgs recoloridos")


HICOLOR = [pathlib.Path("/usr/share/icons/hicolor"), pathlib.Path("/usr/share/icons/Cosmic"), pathlib.Path("/usr/share/icons/Pop"),
           pathlib.Path.home() / ".local/share/icons/hicolor",
           pathlib.Path.home() / ".local/share/flatpak/exports/share/icons/hicolor",
           pathlib.Path("/var/lib/flatpak/exports/share/icons/hicolor")]
DESKTOPS = [pathlib.Path("/usr/share/applications"),
            pathlib.Path.home() / ".local/share/applications",
            pathlib.Path.home() / ".local/share/flatpak/exports/share/applications",
            pathlib.Path("/var/lib/flatpak/exports/share/applications")]


def icones_faltando(destino):
    """Nomes de Icon= dos apps instalados que o tema não tem (cairiam no ícone original)."""
    tem = {p.stem for p in destino.glob("*/*/*.svg")}  # qualquer categoria (apps, places, mimetypes...)
    faltam = set()
    for pasta in DESKTOPS:
        for desk in pasta.glob("*.desktop") if pasta.is_dir() else []:
            m = re.search(r"(?m)^Icon=(.+)$", desk.read_text(errors="ignore"))
            if m and "/" not in m.group(1) and m.group(1).strip() not in tem:
                faltam.add(m.group(1).strip())
    return faltam


def apps_cosmic(destino, nomes=None):
    """Copia ícones de app do hicolor, recoloridos, para dentro do tema.

    Sem `nomes`: só os apps do COSMIC. Com `nomes`: esses ícones (apps sem ícone no Papirus)."""
    melhores = {}
    for raiz in HICOLOR:
        padrao = "*/apps/*.svg" if nomes else "*/apps/com.system76.Cosmic*.svg"
        for svg in sorted(raiz.glob(padrao)):  # ordem alfabética deixa 'scalable'/maiores por último
            if "symbolic" not in svg.name and (nomes is None or svg.stem in nomes):
                melhores[svg.name] = svg
    for pasta in destino.glob("*x*/apps"):
        if pasta.is_symlink():
            continue
        for nome, svg in melhores.items():
            alvo = pasta / nome
            if alvo.is_symlink():
                alvo.unlink()
            alvo.write_text(HEX.sub(lambda m: mapear(m.group(1)), svg.read_text(errors="ignore")))
    print("ícones de app do hicolor", len(melhores))


if __name__ == "__main__":
    if "--incremental" in sys.argv:  # rápido: só os apps novos sem ícone no tema
        faltam = icones_faltando(ICONS / "Papirus-cyberdeck")
        if faltam:
            apps_cosmic(ICONS / "Papirus-cyberdeck", faltam)
        print("faltando:", len(faltam))
        import gerar_placas
        for tema in ("Papirus-cyberdeck", "Papirus-Dark-cyberdeck"):
            print("placas", tema, gerar_placas.aplicar(ICONS / tema, paleta.carregar()))
        sys.exit(0)
    recolorir(origem("Papirus"), ICONS / "Papirus-cyberdeck", "Papirus-cyberdeck", "breeze,hicolor")
    apps_cosmic(ICONS / "Papirus-cyberdeck")
    faltam = icones_faltando(ICONS / "Papirus-cyberdeck")   # apps de terceiros: a reconstrução apagaria os do --incremental
    if faltam:
        apps_cosmic(ICONS / "Papirus-cyberdeck", faltam)
    recolorir(origem("Papirus-Dark"), ICONS / "Papirus-Dark-cyberdeck", "Papirus-Dark-cyberdeck",
              "Papirus-cyberdeck,breeze-dark,hicolor")
    import gerar_placas   # placa chanfrada nos apps e pastas desenhadas (no Dark só o que não é link para o claro)
    for tema in ("Papirus-cyberdeck", "Papirus-Dark-cyberdeck"):
        print("placas", tema, gerar_placas.aplicar(ICONS / tema, paleta.carregar()))
