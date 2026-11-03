"""Gera o tema COSMIC (builder) a partir da paleta ativa (paletas/<nome>.toml)."""
import pathlib
import re
import sys

import paleta

OUT = pathlib.Path(__file__).parent
BASE = pathlib.Path.home() / ".config/cosmic/com.system76.CosmicTheme.Dark.Builder/v1"

# cor do COSMIC -> papel na paleta
PAPEIS = {
    "accent_yellow": "accent", "ext_yellow": "accent",
    "accent_blue": "foco", "ext_blue": "circuito",
    "accent_red": "alerta", "bright_red": "alerta_claro",
    "accent_pink": "rosa", "ext_pink": "rosa",
    "accent_purple": "roxo", "ext_purple": "roxo",
    "accent_green": "verde", "bright_green": "verde",
    "accent_orange": "laranja", "ext_orange": "laranja", "bright_orange": "laranja",
    "neutral_0": "preto", "neutral_1": "fundo_2", "neutral_2": "superficie_1",
    "neutral_3": "superficie_3", "neutral_4": "borda", "neutral_5": "cinza",
    "neutral_6": "fraco", "neutral_7": "muted", "neutral_8": "texto_4",
    "neutral_9": "texto_3", "neutral_10": "quase_branco",
    "gray_1": "sup_d", "gray_2": "sup_c",
}


def rgba(h, a=1.0, indent=4):
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    p = " " * indent
    return f"(\n{p}    red: {r:.7f},\n{p}    green: {g:.7f},\n{p}    blue: {b:.7f},\n{p}    alpha: {a},\n{p})"


def rgb(h, indent=4):  # accent/bg usam Srgb sem alpha
    return re.sub(r"\n\s+alpha: [^\n]+", "", rgba(h, indent=indent))


def campos(pal: dict, nome: str) -> dict:
    palette = (BASE / "palette").read_text()
    palette = re.sub(r'name: "[^"]*"', f'name: "{nome}"', palette)
    for key, papel in PAPEIS.items():
        palette = re.sub(rf"(\n    {key}: )\([^)]*\)", lambda m, c=pal[papel]: m.group(1) + rgba(c), palette)
    return {
        "palette": palette.strip(),
        "spacing": (BASE / "spacing").read_text().strip(),
        "corner_radii": (BASE / "corner_radii").read_text().strip(),
        "neutral_tint": "None",
        "bg_color": f"Some({rgba(pal['fundo'], indent=0)})",
        "primary_container_bg": f"Some({rgba(pal['superficie_2'], indent=0)})",
        "secondary_container_bg": f"Some({rgba(pal['superficie_3'], indent=0)})",
        "text_tint": "None",
        "accent": f"Some({rgb(pal['accent'], indent=0)})",
        "success": f"Some({rgb(pal['verde'], indent=0)})",
        "warning": f"Some({rgb(pal['laranja'], indent=0)})",
        "destructive": f"Some({rgb(pal['alerta'], indent=0)})",
        "is_frosted": "true",  # vidro fosco na gaveta de apps/lançador/painéis
        "gaps": "(16, 24)",
        "active_hint": "2",
        "window_hint": f"Some({rgb(pal['foco'], indent=0)})",
    }


def main(argv):
    nome = paleta.ativa()
    fields = campos(paleta.carregar(nome), nome)
    ind = lambda v: v.replace("\n", "\n    ")  # noqa: E731
    theme = "(\n" + "".join(f"    {k}: {ind(v)},\n" for k, v in fields.items()) + ")\n"
    (OUT / f"tema-{nome}.ron").write_text(theme)  # arquivo de importação manual (Configurações > Aparência)
    if "--aplicar" in argv:  # grava direto no builder do COSMIC (um arquivo por campo)
        for k, v in fields.items():
            (BASE / k).write_text(v)
    print("tema", nome)


if __name__ == "__main__":
    main(sys.argv)
