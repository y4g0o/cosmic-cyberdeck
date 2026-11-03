import re

import paleta

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def test_acid_accent():
    assert paleta.carregar("acid")["accent"] == "#B8FF2E"


def test_nightcity_accent():
    assert paleta.carregar("nightcity")["accent"] == "#FCEE0A"


def test_carregar_usa_ativa():
    assert paleta.carregar() == paleta.carregar(paleta.ativa())


def test_toda_chave_e_hex_valido():
    for nome in ("acid", "nightcity"):
        for k, v in paleta.carregar(nome).items():
            assert HEX.match(v), f"{nome}.{k}={v}"


def test_mesmo_conjunto_de_chaves():
    assert paleta.carregar("acid").keys() == paleta.carregar("nightcity").keys()


def test_chaves_obrigatorias():
    p = paleta.carregar("acid")
    obrig = ["fundo", "accent", "foco", "roxo_profundo", "circuito", "alerta", "texto",
             "superficie_1", "superficie_2", "superficie_3"]
    obrig += [f"ansi_{i}" for i in range(16)]
    assert set(obrig) <= set(p)


def test_acid_valores_base():
    p = paleta.carregar("acid")
    assert (p["fundo"], p["foco"], p["roxo_profundo"], p["circuito"], p["alerta"], p["texto"]) == (
        "#060609", "#7B4DFF", "#2B1B6E", "#3C7BFF", "#FF2D55", "#E8EAF2")


def test_hex_rgb():
    assert paleta.hex_rgb("#B8FF2E") == (184, 255, 46)
