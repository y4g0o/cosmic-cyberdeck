"""Aplica uma paleta ao sistema inteiro: renderiza templates/ e roda os geradores.

Uso: python3 aplicar.py [--paleta acid|nightcity] [--seco [--destino-seco DIR]]
--seco escreve os arquivos renderizados em DIR (padrão saida/seco/) e não toca no sistema.
Para instalar com backup e desfazer depois, use install.py (ele chama este arquivo).
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import marca
import paleta

RAIZ = Path(__file__).resolve().parent
TPL = RAIZ / "templates"
H = Path.home()
COSMIC = H / ".config/cosmic"

# template -> destinos reais
ALVOS = {
    "starship.toml.tpl": [H / ".config/starship.toml"],
    "btop.theme.tpl": [H / ".config/btop/themes/cyberdeck.theme"],
    "cava.tpl": [H / ".config/cava/config"],
    "fish.fish.tpl": [H / ".config/fish/conf.d/90-cyberdeck-cores.fish"],
    "spicetify-color.ini.tpl": [H / ".config/spicetify/Themes/cyberdeck/color.ini"],
    "spicetify-user.css.tpl": [H / ".config/spicetify/Themes/cyberdeck/user.css"],
    "fastfetch.jsonc.tpl": [H / ".config/fastfetch/config.jsonc"],
    "brave-manifest.json.tpl": [RAIZ / "brave-theme/manifest.json"],
    "ntp.css.tpl": [RAIZ / "brave-ntp/ntp.css"],
    "newtab.html.tpl": [RAIZ / "brave-ntp/newtab.html"],
    "fish-papel.fish": [H / ".config/fish/conf.d/91-cyberdeck-papel.fish"],
    "fish-comando.fish": [H / ".config/fish/conf.d/91-cyberdeck-comando.fish"],
}
TERM = COSMIC / "com.system76.CosmicTerm/v1"

_PH = re.compile(r"\{\{(rgb:|hex:)?([a-z0-9_]+)\}\}")


def renderizar(tpl: str, pal: dict) -> str:
    """{{RAIZ}} = pasta do repositório; {{HOME}} = pasta do usuário; {{ASSINATURA}} = assinatura do config.toml;
    o resto ({{accent}}, {{hex:foco}}, {{rgb:texto}}) são cores da paleta."""
    tpl = tpl.replace("{{RAIZ}}", str(RAIZ)).replace("{{HOME}}", str(H)).replace("{{ASSINATURA}}", marca.assinatura())

    def sub(m):
        cor = pal[m.group(2)]  # KeyError se o placeholder não existir
        if m.group(1) == "rgb:":
            return ", ".join(str(x) for x in paleta.hex_rgb(cor))
        if m.group(1) == "hex:":
            return cor.lstrip("#")
        return cor
    return _PH.sub(sub, tpl)


def _arquivos(pal: dict) -> dict[Path, str]:
    """Todos os arquivos de config gerados por template: destino -> conteúdo."""
    saida = {}
    for nome, destinos in ALVOS.items():
        txt = renderizar((TPL / nome).read_text(), pal)
        for d in destinos:
            saida[d] = txt
    esquema = renderizar((TPL / "terminal.ron.tpl").read_text(), pal).strip()
    saida[TERM / "color_schemes_dark"] = "{\n    1: " + esquema.replace("\n", "\n    ") + ",\n}\n"
    saida[TERM / "syntax_theme_dark"] = '"cyberdeck"'
    saida[TERM / "opacity"] = "85"
    return saida


def _falta_o_app(d: Path) -> bool:
    """O destino é de um app que não está instalado? (Spicetify ausente). As subpastas que o próprio tema
    cria (btop/themes, cava, fastfetch...) não contam: são recriadas."""
    if d.is_relative_to(H / ".config/spicetify"):
        return not (H / ".config/spicetify").is_dir()
    return False


def _no_seco(d: Path, destino_seco: Path) -> Path:
    """Onde o modo --seco grava o destino `d`: arquivos do HOME em DIR/casa/..., os do repositório em DIR/repo/..."""
    if d.is_relative_to(RAIZ):
        return destino_seco / "repo" / d.relative_to(RAIZ)
    return destino_seco / "casa" / d.relative_to(H)


def _escrever(arquivos: dict[Path, str], destino_seco: Path | None):
    for d, txt in arquivos.items():
        alvo = _no_seco(d, destino_seco) if destino_seco else d
        if not destino_seco and _falta_o_app(d):
            continue
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(txt)


def _btop_conf():
    conf = H / ".config/btop/btop.conf"
    if conf.exists():
        conf.write_text(re.sub(r'(?m)^color_theme = .*$', 'color_theme = "cyberdeck"', conf.read_text()))


def _vscode(pal: dict):
    p = H / ".config/Code/User/settings.json"
    if not p.exists():
        return
    s = json.loads(p.read_text())
    s["workbench.colorCustomizations"] = {
        "editor.background": pal["fundo"], "sideBar.background": pal["superficie_1"],
        "activityBar.background": pal["fundo_2"], "statusBar.background": pal["superficie_2"],
        "titleBar.activeBackground": pal["fundo_2"], "panel.background": pal["fundo"],
        "terminal.background": pal["fundo"], "focusBorder": pal["foco"],
        "activityBar.foreground": pal["accent"], "statusBar.foreground": pal["texto"],
        "editorCursor.foreground": pal["accent"], "selection.background": pal["roxo_profundo"],
        "button.background": pal["accent"], "button.foreground": pal["fundo"],
        "tab.activeBorderTop": pal["accent"], "list.activeSelectionBackground": pal["roxo_profundo"],
    }
    p.write_text(json.dumps(s, indent=4, ensure_ascii=False))


def _rodar(*cmd):
    print("$", " ".join(str(c) for c in cmd))
    subprocess.run([str(c) for c in cmd], check=False, cwd=RAIZ)


def paleta_do_tema(builder: str) -> str:
    """O Builder guarda a paleta como Dark((...)); o tema espera só a struct (...)."""
    m = re.fullmatch(r"\s*(?:Dark|Light)\((.*)\)\s*", builder, re.S)
    return (m.group(1) if m else builder.strip()) + "\n"


def avisar_abertos(nome: str):
    """Apps já abertos pegam a paleta nova: fish relê as cores (variável universal; a hora garante que ela mude),
    cava relê as cores (USR2). O HUD percebe sozinho pela data de paletas/ATIVA."""
    _rodar("fish", "-c", f"set -U cyberdeck_paleta {nome}:(date +%s)")
    _rodar("pkill", "-USR2", "-x", "cava")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--paleta", default=None)
    ap.add_argument("--seco", action="store_true")
    ap.add_argument("--destino-seco", default=str(RAIZ / "saida/seco"))
    a = ap.parse_args(argv)
    nome = a.paleta or paleta.ativa()
    pal = paleta.carregar(nome)
    arquivos = _arquivos(pal)
    if a.seco:
        _escrever(arquivos, Path(a.destino_seco))
        return
    (RAIZ / "paletas/ATIVA").write_text(nome + "\n")
    _escrever(arquivos, None)
    _btop_conf()
    _vscode(pal)
    py = sys.executable
    _rodar(py, "gerar_temas.py", "--aplicar")
    _rodar(py, "recolorir_tema.py", "--aplicar")
    (COSMIC / "com.system76.CosmicTheme.Dark/v1/palette").write_text(
        paleta_do_tema((COSMIC / "com.system76.CosmicTheme.Dark.Builder/v1/palette").read_text()))
    _rodar(py, "gerar_icones.py")
    for t in ("Papirus-cyberdeck", "Papirus-Dark-cyberdeck"):
        _rodar("gtk-update-icon-cache", "-f", "-q", H / ".local/share/icons" / t)
    _rodar(py, "gerar_cursor.py")
    _rodar(py, "gerar_logo.py")
    _rodar(py, "gerar_poster.py", "--aplicar")   # também grava o fundo da nova aba do Brave
    if (H / ".spicetify/spicetify").exists():
        _rodar(H / ".spicetify/spicetify", "refresh")
    _rodar("pkill", "-x", "cosmic-panel")
    avisar_abertos(nome)
    print(f"paleta '{nome}' aplicada. Brave, Spotify e btop só mudam ao reabrir; cursor completo após novo login.")


if __name__ == "__main__":
    main()
