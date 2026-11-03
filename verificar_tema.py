"""Confere se o tema compilado do COSMIC continua inteiro depois de atualizações e conserta se não estiver.

Uma versão nova do COSMIC pode trazer chaves que o nosso tema não tem (ex.: list_button no 1.11): sem elas o
tema inteiro dá erro ao carregar. A paleta também precisa estar como struct (...), não Dark((...)).
Uso: python3 verificar_tema.py [--consertar]   (sai com 1 se encontrou problema)
"""
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
COSMIC = Path.home() / ".config/cosmic"
USUARIO = COSMIC / "com.system76.CosmicTheme.Dark/v1"
SISTEMA = Path("/usr/share/cosmic/com.system76.CosmicTheme.Dark/v1")


def problemas(usuario: Path, sistema: Path) -> list[str]:
    chaves = sorted(sistema.iterdir()) if sistema.is_dir() else []
    achados = [f"chave nova do COSMIC: {f.name}" for f in chaves if not (usuario / f.name).exists()]
    pal = usuario / "palette"
    if pal.exists() and pal.read_text().lstrip().startswith(("Dark(", "Light(")):
        achados.append("paleta no formato do Builder")
    return achados


def consertar():
    py = sys.executable
    subprocess.run([py, str(RAIZ / "recolorir_tema.py"), "--aplicar"], check=True, cwd=RAIZ)
    sys.path.insert(0, str(RAIZ))
    import aplicar
    builder = COSMIC / "com.system76.CosmicTheme.Dark.Builder/v1/palette"
    if builder.exists():
        (USUARIO / "palette").write_text(aplicar.paleta_do_tema(builder.read_text()))
    modo = COSMIC / "com.system76.CosmicTheme.Mode/v1/is_dark"   # alternar faz o COSMIC recarregar o tema
    modo.write_text("false")
    modo.write_text("true")


def main(argv):
    achados = problemas(USUARIO, SISTEMA)
    for a in achados:
        print(a)
    if achados and "--consertar" in argv:
        consertar()
        print("tema consertado")
        return 0
    return 1 if achados else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
