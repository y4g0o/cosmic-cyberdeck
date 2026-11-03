#!/usr/bin/env python3
"""Instala o cosmic-cyberdeck com backup, e desfaz restaurando o backup.

  python3 install.py --dry-run [--paleta acid]   mostra o que mudaria e renderiza tudo em saida/seco/ (não toca no sistema)
  python3 install.py [--paleta acid] [--autostart] [--shortcut] [--yes]
                                                 backup em ~/.local/share/cosmic-cyberdeck/backups/<data>/ e aplica
  python3 install.py --uninstall                 restaura o backup mais recente ainda não restaurado
  python3 install.py --restore --backup NOME     restaura um backup específico (ver --list-backups)
  python3 install.py --list-backups
  python3 install.py --spotify-hook              gera o gancho do apt para o Spicetify e mostra o comando com sudo

--autostart: no login roda a manutenção (manutencao.sh) e monta o layout (precisa do .venv com pywayland).
--shortcut:  Super+Y monta o layout (substitui o arquivo de atalhos personalizados do COSMIC; vai para o backup).
Passos com sudo (tela de boot, gancho do apt) nunca são executados aqui: só mostrados.
"""
import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import aplicar  # noqa: E402
import paleta  # noqa: E402

COSMIC = ".config/cosmic"
# pastas inteiras que os geradores reescrevem (backup da pasta toda)
PASTAS = [
    f"{COSMIC}/com.system76.CosmicTheme.Dark/v1",
    f"{COSMIC}/com.system76.CosmicTheme.Dark.Builder/v1",
    f"{COSMIC}/com.system76.CosmicBackground/v1",
]
# arquivos alterados fora dos templates
EXTRAS = [".config/btop/btop.conf", ".config/Code/User/settings.json", ".config/fastfetch/logo.txt"]
# pastas criadas do zero pelos geradores: sem backup (são nossas), removidas ao desinstalar se não existiam antes
GERADAS = [".local/share/icons/Papirus-cyberdeck", ".local/share/icons/Papirus-Dark-cyberdeck",
           ".local/share/icons/Bibata-Modern-cyberdeck", ".local/share/cosmic-cyberdeck/posters"]
AUTOSTART = ".config/autostart/cosmic-cyberdeck.desktop"
ATALHOS = f"{COSMIC}/com.system76.CosmicSettings.Shortcuts/v1/custom"


def dados(home: Path) -> Path:
    base = os.environ.get("XDG_DATA_HOME")
    return (Path(base) if base else home / ".local/share") / "cosmic-cyberdeck"


def dir_backups(home: Path) -> Path:
    return dados(home) / "backups"


def alvos(home: Path, pal: dict, autostart=False, atalho=False) -> list[tuple[str, str]]:
    """(caminho relativo ao HOME, 'file'|'dir') de tudo o que a instalação pode mudar."""
    arquivos = sorted({str(d.relative_to(aplicar.H)) for d in aplicar._arquivos(pal)
                       if d.is_relative_to(aplicar.H) and not d.is_relative_to(RAIZ)})
    lista = [(p, "dir") for p in PASTAS]
    cobertos = tuple(p + "/" for p in PASTAS)
    lista += [(p, "file") for p in arquivos + EXTRAS if not p.startswith(cobertos)]
    if autostart:
        lista.append((AUTOSTART, "file"))
    if atalho:
        lista.append((ATALHOS, "file"))
    return lista


def fazer_backup(home: Path, lista, nome_paleta: str, agora=None) -> Path:
    """Copia cada alvo que existe para backups/<data>/files/ e grava o manifesto (o que existia e o que não)."""
    pasta = dir_backups(home) / time.strftime("%Y%m%d-%H%M%S", time.localtime(agora))
    while pasta.exists():   # dois backups no mesmo segundo
        pasta = pasta.with_name(pasta.name + "-1")
    (pasta / "files").mkdir(parents=True)
    entradas = []
    for rel, tipo in lista:
        origem = home / rel
        existia = origem.exists() or origem.is_symlink()
        if existia:
            destino = pasta / "files" / rel
            destino.parent.mkdir(parents=True, exist_ok=True)
            if origem.is_dir() and not origem.is_symlink():
                shutil.copytree(origem, destino, symlinks=True)
            else:
                shutil.copy2(origem, destino, follow_symlinks=False)
        entradas.append({"path": rel, "kind": tipo, "existed": existia})
    geradas = [{"path": g, "existed": (home / g).exists()} for g in GERADAS]
    manifesto = {"created": time.strftime("%Y-%m-%dT%H:%M:%S"), "palette": nome_paleta,
                 "entries": entradas, "generated": geradas, "restored": None}
    (pasta / "manifest.json").write_text(json.dumps(manifesto, indent=2, ensure_ascii=False))
    return pasta


def backups(home: Path) -> list[Path]:
    d = dir_backups(home)
    return sorted(p for p in d.iterdir() if (p / "manifest.json").exists()) if d.is_dir() else []


def _remover(p: Path):
    if p.is_symlink() or p.is_file():
        p.unlink()
    elif p.is_dir():
        shutil.rmtree(p)


def restaurar(home: Path, pasta: Path) -> list[str]:
    """Põe de volta o que o backup guardou e apaga o que a instalação criou. Devolve o que foi feito."""
    m = json.loads((pasta / "manifest.json").read_text())
    feito = []
    for e in m["entries"]:
        alvo = home / e["path"]
        if e["existed"]:
            copia = pasta / "files" / e["path"]
            _remover(alvo)
            alvo.parent.mkdir(parents=True, exist_ok=True)
            if copia.is_dir() and not copia.is_symlink():
                shutil.copytree(copia, alvo, symlinks=True)
            else:
                shutil.copy2(copia, alvo, follow_symlinks=False)
            feito.append(f"restaurado  ~/{e['path']}")
        elif alvo.exists() or alvo.is_symlink():
            _remover(alvo)
            feito.append(f"removido    ~/{e['path']}")
    for g in m.get("generated", []):
        alvo = home / g["path"]
        if not g["existed"] and alvo.exists():
            _remover(alvo)
            feito.append(f"removido    ~/{g['path']}")
    m["restored"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    (pasta / "manifest.json").write_text(json.dumps(m, indent=2, ensure_ascii=False))
    return feito


def ultimo_nao_restaurado(home: Path) -> Path | None:
    for p in reversed(backups(home)):
        if not json.loads((p / "manifest.json").read_text()).get("restored"):
            return p
    return None


def guardar_tema_original(home: Path):
    """Cópia do tema escuro do COSMIC antes do primeiro tema nosso: o recolorir_tema.py parte dela."""
    atual = home / f"{COSMIC}/com.system76.CosmicTheme.Dark/v1"
    destino = dados(home) / "original/CosmicTheme.Dark.v1"
    if destino.exists() or not atual.is_dir():
        return
    nome = (atual / "name").read_text().strip().strip('"') if (atual / "name").exists() else ""
    if (paleta.DIR / f"{nome}.toml").exists():   # já é um tema do cyberdeck: o padrão do sistema serve de origem
        return
    shutil.copytree(atual, destino, symlinks=True)


def escrever_extras(home: Path, autostart: bool, atalho: bool):
    pal = paleta.carregar()
    if autostart:
        d = home / AUTOSTART
        d.parent.mkdir(parents=True, exist_ok=True)
        d.write_text(aplicar.renderizar((RAIZ / "templates/autostart-cyberdeck.desktop").read_text(), pal))
    if atalho:
        d = home / ATALHOS
        d.parent.mkdir(parents=True, exist_ok=True)
        d.write_text(aplicar.renderizar((RAIZ / "templates/cosmic-atalhos-custom.ron").read_text(), pal))


def gancho_spotify() -> Path:
    import getpass
    saida = RAIZ / "saida/apt-99cyberdeck-spotify"
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text((RAIZ / "templates/apt-99cyberdeck-spotify").read_text().replace("{{USUARIO}}", getpass.getuser()))
    return saida


def parece_cosmic(home: Path) -> bool:
    return "COSMIC" in os.environ.get("XDG_CURRENT_DESKTOP", "").upper() or (home / COSMIC).is_dir()


def main(argv=None, home: Path | None = None) -> int:
    ap = argparse.ArgumentParser(description="cosmic-cyberdeck: install with backup / restore")
    ap.add_argument("--paleta", "--palette", dest="paleta", default=None, help="paletas/<nome>.toml (padrão: a ATIVA)")
    ap.add_argument("--dry-run", action="store_true", help="só mostra e renderiza em saida/seco/")
    ap.add_argument("--uninstall", "--restore", dest="restaurar", action="store_true", help="restaura um backup")
    ap.add_argument("--backup", help="nome do backup a restaurar (padrão: o mais recente não restaurado)")
    ap.add_argument("--list-backups", action="store_true")
    ap.add_argument("--autostart", action="store_true", help="manutenção + layout no login")
    ap.add_argument("--shortcut", action="store_true", help="Super+Y monta o layout")
    ap.add_argument("--spotify-hook", action="store_true", help="gera o gancho do apt do Spicetify")
    ap.add_argument("--yes", "-y", action="store_true", help="não pergunta antes de aplicar")
    ap.add_argument("--force", action="store_true", help="instala mesmo sem detectar o COSMIC")
    a = ap.parse_args(argv)
    home = home or Path.home()

    if a.list_backups:
        for p in backups(home):
            m = json.loads((p / "manifest.json").read_text())
            print(f"{p.name}  paleta={m['palette']}  restaurado={m.get('restored') or 'não'}")
        return 0

    if a.spotify_hook:
        s = gancho_spotify()
        print(f"gerado {s}\nInstale (sudo, uma vez):\n  sudo cp '{s}' /etc/apt/apt.conf.d/99cyberdeck-spotify")
        return 0

    if a.restaurar:
        pasta = dir_backups(home) / a.backup if a.backup else ultimo_nao_restaurado(home)
        if not pasta or not (pasta / "manifest.json").exists():
            print("nenhum backup para restaurar em", dir_backups(home))
            return 1
        print(f"restaurando {pasta}")
        for linha in restaurar(home, pasta):
            print(" ", linha)
        print("Pronto. Faça logout/login (ou alterne claro/escuro) para o COSMIC recarregar o tema.\n"
              "Tela de boot e sons, se instalados, têm desfazer próprio (veja o README).")
        return 0

    nome = a.paleta or paleta.ativa()
    pal = paleta.carregar(nome)
    lista = alvos(home, pal, a.autostart, a.shortcut)

    if a.dry_run:
        print(f"[dry-run] paleta '{nome}'. Nada será alterado.\nArquivos/pastas que a instalação mudaria:")
        for rel, tipo in lista:
            estado = "backup + sobrescrever" if (home / rel).exists() else "criar"
            print(f"  {estado:<22} ~/{rel}{'/' if tipo == 'dir' else ''}")
        for g in GERADAS:
            print(f"  {'gerar (removido ao desinstalar)':<22} ~/{g}/")
        print(f"  {'reescrever no repositório':<22} paletas/ATIVA, brave-theme/manifest.json, brave-ntp/*")
        print("Também: reinicia o cosmic-panel, avisa fish/cava abertos e, se houver Spicetify, roda `spicetify refresh`.")
        seco = RAIZ / "saida/seco"
        aplicar.main(["--seco", "--paleta", nome, "--destino-seco", str(seco)])
        print(f"Configs renderizadas para conferir em {seco}/")
        return 0

    if not parece_cosmic(home) and not a.force:
        print("COSMIC não detectado (XDG_CURRENT_DESKTOP / ~/.config/cosmic). Use --force para instalar mesmo assim.")
        return 1
    if not a.yes:
        r = input(f"Aplicar a paleta '{nome}' ({len(lista)} alvos; backup antes)? [y/N] ")
        if r.strip().lower() not in ("y", "s", "yes", "sim"):
            print("cancelado")
            return 1
    pasta = fazer_backup(home, lista, nome)
    print(f"backup: {pasta}")
    guardar_tema_original(home)
    aplicar.main(["--paleta", nome])
    escrever_extras(home, a.autostart, a.shortcut)
    print(f"\nDesfazer: python3 {RAIZ / 'install.py'} --uninstall\n"
          "Alterne claro/escuro uma vez (ou faça logout/login) para o compositor recarregar os vãos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
