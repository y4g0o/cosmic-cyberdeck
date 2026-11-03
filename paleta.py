"""Paletas como fonte de verdade: lê paletas/<nome>.toml."""
import tomllib
from pathlib import Path

DIR = Path(__file__).parent / "paletas"


def ativa() -> str:
    return (DIR / "ATIVA").read_text().strip()


def carregar(nome: str | None = None) -> dict[str, str]:
    with open(DIR / f"{nome or ativa()}.toml", "rb") as f:
        return tomllib.load(f)


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
