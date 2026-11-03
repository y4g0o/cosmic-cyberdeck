"""Recolore o tema COSMIC já compilado (Dark/v1) com a paleta ativa, sem depender do app de Configurações.

Parte sempre do tema cosmic-dark original (a cópia que o install.py guarda na 1ª instalação; sem ela, o padrão
do sistema em /usr/share/cosmic) e troca: família do accent -> accent da paleta;
cinzas de superfície -> tons escuros com o matiz de superficie_2; cinzas de texto -> matiz de texto.
"""
import os
import pathlib
import re
import sys

import layout
import paleta

D = pathlib.Path.home() / ".config/cosmic/com.system76.CosmicTheme.Dark/v1"
DADOS = pathlib.Path(os.environ.get("XDG_DATA_HOME") or pathlib.Path.home() / ".local/share") / "cosmic-cyberdeck"
ORIGEM = DADOS / "original/CosmicTheme.Dark.v1"   # tema cosmic-dark puro, guardado pelo install.py antes de mexer
SISTEMA = pathlib.Path("/usr/share/cosmic/com.system76.CosmicTheme.Dark/v1")  # traz chaves de versões novas
ALFA_VIDRO = 0.82  # opacidade do fundo/containers com vidro fosco (gaveta de apps, lançador)
PAT = re.compile(r"red: ([\d.e-]+),(\s*)green: ([\d.e-]+),(\s*)blue: ([\d.e-]+),(\s*)alpha: ([\d.e-]+)")


def _norm(hexcor):
    c = [x / 255 for x in paleta.hex_rgb(hexcor)]
    m = max(c) or 1.0
    return tuple(x / m for x in c)


def mapeador(pal: dict):
    acc = tuple(x / 255 for x in paleta.hex_rgb(pal["accent"]))
    tint_sup, tint_txt = _norm(pal["superficie_2"]), _norm(pal["texto"])
    claro = tuple(min(1.0, a * 0.55 + 0.45) for a in acc)

    def mapear(r, g, b):
        if r > 0.4 and g < 0.2 and b > 0.25 and r > b:          # família do accent magenta original
            k = r / 0.9720629
            return tuple(min(1.0, c * k) for c in acc)
        if r > 0.95 and 0.45 < g < 0.65 and b > 0.65:           # texto rosado sobre accent
            return claro
        if abs(r - g) < 0.01 and abs(g - b) < 0.01 and r > 0.005:  # cinzas
            v = r
            if v < 0.5:                                          # superfícies: escuras, mais camadas
                v = v * 0.28 if v < 0.106 else 0.03 + (v - 0.106) * 1.25
                return tuple(min(1.0, v * t + 0.008) for t in tint_sup)
            return tuple(min(1.0, v * (0.9 + 0.1 * t)) for t in tint_txt)  # texto
        return (r, g, b)

    return mapear


def fontes_do_tema(d, origem, sistema):
    """Arquivo de partida de cada chave do tema: o original guardado; para chaves que só versões novas do
    COSMIC têm (ex.: list_button), o padrão do sistema."""
    nomes = {f.name for base in (d, sistema) if base.is_dir() for f in base.iterdir()}
    return {n: next(b / n for b in (origem, sistema, d) if (b / n).exists()) for n in sorted(nomes)}


def main(argv):
    nome = paleta.ativa()
    pal = paleta.carregar(nome)
    mapear = mapeador(pal)

    def sub(m):
        r, g, b = (float(m.group(i)) for i in (1, 3, 5))
        nr, ng, nb = mapear(r, g, b)
        return f"red: {nr:.7f},{m.group(2)}green: {ng:.7f},{m.group(4)}blue: {nb:.7f},{m.group(6)}alpha: {m.group(7)}"

    for nome_arq, fonte in fontes_do_tema(D, ORIGEM, SISTEMA).items():
        f = D / nome_arq
        t = fonte.read_text()
        n = len(PAT.findall(t))
        novo = PAT.sub(sub, t)
        assert len(PAT.findall(novo)) == n, f
        if "--aplicar" in argv and (novo != t or not f.exists()):
            f.write_text(novo)

    if "--aplicar" in argv:
        fr, fg, fb = (x / 255 for x in paleta.hex_rgb(pal["foco"]))
        (D / "active_hint").write_text("2")
        (D / "window_hint").write_text(f"Some((\n    red: {fr:.7f},\n    green: {fg:.7f},\n    blue: {fb:.7f},\n))")
        (D / "name").write_text(f'"{nome}"')
        L = layout.carregar_layout()
        (D / "gaps").write_text(f"({L.gap_externo}, {L.gap_interno})")   # vãos vêm do layout.toml
        (D / "is_frosted").write_text("true")
        for nome_arq in ("background", "primary", "secondary"):   # só o "base" de cima de cada container
            f = D / nome_arq
            f.write_text(re.sub(r"(base: \(\s*red: [\d.]+,\s*green: [\d.]+,\s*blue: [\d.]+,\s*alpha: )[\d.]+",
                                lambda m: m.group(1) + str(ALFA_VIDRO), f.read_text(), count=1))
    print("tema compilado recolorido:", nome)


if __name__ == "__main__":
    main(sys.argv)
