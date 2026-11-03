"""Gera os pôsteres (paleta ativa + layout.toml + fotos/) e, com --aplicar, põe como papel de parede.

Uso: python3 gerar_poster.py [--aplicar] [--destino DIR] [--todas]
  --destino DIR  grava os pôsteres em DIR (padrão: ~/.local/share/cosmic-cyberdeck/posters)
  --todas        gera para todas as saídas do layout.toml, mesmo desconectadas (ex.: prévias sem monitor)
Sem --aplicar nada fora do repositório e do destino é tocado.
"""
import os
import re
import sys
from pathlib import Path

import layout
import paleta
from poster import compor

RAIZ = Path(__file__).resolve().parent
DADOS = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "cosmic-cyberdeck"
OUT = DADOS / "posters"
CFG = Path.home() / ".config/cosmic/com.system76.CosmicBackground/v1"


def saida_do_brave(L, saidas) -> str | None:
    """Monitor cujo pôster vira o fundo da nova aba do Brave: o que tem o slot `brave`, senão o primeiro."""
    for s in saidas:
        if "brave" in L.slots(s):
            return s
    return saidas[0] if saidas else None


def aplicar_wallpapers(feitas, cfg: Path = CFG):
    """Troca o caminho da imagem em output.<saida>; a entrada `all` recebe o pôster da primeira saída."""
    for i, (saida, caminho) in enumerate(feitas):
        entradas = [cfg / f"output.{saida}"] + ([cfg / "all"] if i == 0 else [])
        for e in entradas:
            if e.exists():
                e.write_text(re.sub(r'Path\("[^"]*"\)', f'Path("{caminho}")', e.read_text()))


def main(argv):
    L = layout.carregar_layout()
    out = Path(argv[argv.index("--destino") + 1]) if "--destino" in argv else OUT
    conectadas = [] if "--todas" in argv else layout.saidas_conectadas()
    saidas = [s for s in conectadas if s in L.saidas()] or L.saidas()
    fotos = RAIZ / "fotos"
    feitas = compor.gerar(saidas, L, paleta.carregar(), fotos if fotos.is_dir() else None, out)
    for s, c in feitas:
        print(s, "->", c)
    if "--aplicar" in argv:
        aplicar_wallpapers(feitas)
        em_uso = {Path(m) for e in CFG.glob("*") if e.is_file() for m in re.findall(r'Path\("([^"]*)"\)', e.read_text())}
        compor.limpar_antigos(out, manter=em_uso | {c for _, c in feitas})
        brave = saida_do_brave(L, [s for s, _ in feitas])
        for s, c in feitas:
            if s == brave and (RAIZ / "brave-ntp").is_dir():
                from PIL import Image
                Image.open(c).convert("RGB").save(RAIZ / "brave-ntp/fundo.jpg", quality=82)
    return feitas


if __name__ == "__main__":
    main(sys.argv)
