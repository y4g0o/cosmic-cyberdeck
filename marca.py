"""Configuração do usuário (config.toml): a assinatura do tema e as opções do HUD.

A variável de ambiente CYBERDECK_SIGNATURE sobrepõe a assinatura (útil para testar sem editar o arquivo).
"""
import os
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ARQUIVO = RAIZ / "config.toml"
PADRAO = "CYBERDECK"


def config(arquivo: Path = ARQUIVO) -> dict:
    try:
        return tomllib.loads(Path(arquivo).read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def assinatura(arquivo: Path = ARQUIVO) -> str:
    s = os.environ.get("CYBERDECK_SIGNATURE") or config(arquivo).get("assinatura") or PADRAO
    return str(s).strip().upper()[:24] or PADRAO


def hud(arquivo: Path = ARQUIVO) -> dict:
    return config(arquivo).get("hud", {})
