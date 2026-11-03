import sys
from pathlib import Path

import pytest
from PIL import Image, ImageChops

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from layout import Rect  # noqa: E402
from poster import modulos as m  # noqa: E402

PAL = {
    "fundo": "#060609", "accent": "#B8FF2E", "foco": "#7B4DFF",
    "roxo_profundo": "#2B1B6E", "circuito": "#3C7BFF", "alerta": "#FF2D55",
    "texto": "#E8EAF2", "superficie_1": "#0C0C14", "superficie_2": "#12121E",
    "superficie_3": "#1A1A2A",
}
R = Rect(20, 20, 300, 200)
DADOS = {"NAME": "CYBERDECK", "FUNCTION": "OPERADOR", "STATE": "ONLINE",
         "CLEARANCE": "A-34", "LOCATION": "SETOR 07"}


def tela():
    return Image.new("RGB", (400, 300), PAL["fundo"])


def igual(a, b):
    return ImageChops.difference(a, b).getbbox() is None


def _uso(nome):
    return {
        "moldura": lambda i, s: m.moldura(i, R, PAL),
        "ficha": lambda i, s: m.ficha_operador(i, R, PAL, DADOS),
        "barras": lambda i, s: m.codigo_barras(i, R, PAL, s),
        "onda": lambda i, s: m.onda(i, R, PAL, s),
        "micro": lambda i, s: m.microtexto(i, R, PAL, s),
        "circ": lambda i, s: m.circuito(i, R, PAL, s, [(30, 40), (300, 200), (150, 100)]),
        "titulo": lambda i, s: m.titulo(i, (30, 30), "CYBERDECK // SISTEMA", PAL, 28),
    }[nome]


@pytest.mark.parametrize("nome", ["moldura", "ficha", "barras", "onda", "micro", "circ", "titulo"])
def test_deterministico(nome):
    f = _uso(nome)
    a, b, c = tela(), tela(), tela()
    f(a, 7)
    f(b, 7)
    f(c, 8)
    assert a.getbbox() and not igual(a, tela())
    assert igual(a, b)
    if nome in ("barras", "onda", "micro", "circ"):
        assert not igual(a, c)


def test_dither_duas_cores():
    src = m.placeholder_foto(Rect(0, 0, 120, 90), 3)
    out = m.dither(src, Rect(0, 0, 120, 90), "#B8FF2E")
    cores = {c for _, c in out.convert("RGB").getcolors()}
    assert cores <= {(6, 6, 9), (184, 255, 46)}
    assert len(cores) == 2
    assert out.size == (120, 90)


def test_placeholder_deterministico():
    r = Rect(0, 0, 80, 60)
    assert igual(m.placeholder_foto(r, 1).convert("RGB"), m.placeholder_foto(r, 1).convert("RGB"))
    assert not igual(m.placeholder_foto(r, 1).convert("RGB"), m.placeholder_foto(r, 2).convert("RGB"))


def test_circuito_toca_entradas():
    pts = [(30, 40), (300, 200), (150, 100), (60, 210)]
    img = tela()
    m.circuito(img, R, PAL, 5, pts)
    for p in pts:
        assert img.getpixel(p) != (6, 6, 9), p


def test_nenhum_texto_proibido():
    m._LOG_TEXTOS.clear()
    img = tela()
    for n in ["ficha", "micro", "titulo", "barras", "onda", "circ", "moldura"]:
        _uso(n)(img, 11)
    assert m._LOG_TEXTOS
    for t in m._LOG_TEXTOS:
        for p in m.TEXTOS_PROIBIDOS:
            assert p not in t.lower()


@pytest.mark.parametrize("txt", ["Cyberpunk", "NIGHT CITY", "arasaka corp", "2077"])
def test_titulo_proibido_levanta(txt):
    with pytest.raises(ValueError):
        m.titulo(tela(), (10, 10), txt, PAL, 20)


def test_ficha_proibida_levanta():
    with pytest.raises(ValueError):
        m.ficha_operador(tela(), R, PAL, {**DADOS, "LOCATION": "Night City"})


def test_texto_publico_valida_termos_proibidos():
    from PIL import Image
    from poster import modulos
    img = Image.new("RGB", (200, 60), "#060609")
    modulos.texto(img, (4, 4), "NODE 07", "#B8FF2E", "mono", 14)
    assert img.getbbox() is not None
    import pytest
    with pytest.raises(ValueError):
        modulos.texto(img, (4, 4), "night city", "#B8FF2E", "mono", 14)


def test_texto_vertical_empilha_caracteres():
    from PIL import Image
    from poster import modulos
    img = Image.new("RGB", (60, 400), "#000000")
    modulos.texto_vertical(img, (10, 10), "監視中", "#FFFFFF", "cjk", 40)
    x0, y0, x1, y1 = img.getbbox()
    assert y1 - y0 > 2 * (x1 - x0)


def test_ficha_sem_rotulo_copiado_da_referencia():
    from PIL import Image
    from layout import Rect
    from poster import modulos
    modulos._LOG_TEXTOS.clear()
    img = Image.new("RGB", (600, 400), "#060609")
    pal = {k: "#B8FF2E" for k in ("fundo", "accent", "foco", "roxo_profundo", "circuito", "alerta", "texto",
                                  "superficie_1", "superficie_2", "superficie_3")}
    modulos.ficha_operador(img, Rect(0, 0, 600, 400), pal, {"NAME": "CYBERDECK"})
    log = " ".join(modulos._LOG_TEXTOS)
    assert "SUBJECT" not in log and "DOSSIÊ" in log


def test_ficha_usa_foto_quando_fornecida():
    from PIL import Image
    from layout import Rect
    from poster import modulos
    pal = {k: v for k, v in zip(("fundo", "accent", "foco", "roxo_profundo", "circuito", "alerta", "texto",
                                 "superficie_1", "superficie_2", "superficie_3"),
                                ("#060609", "#B8FF2E", "#7B4DFF", "#2B1B6E", "#3C7BFF", "#FF2D55", "#E8EAF2",
                                 "#0D0C14", "#161422", "#221F33"))}
    r = Rect(0, 0, 600, 400)
    a = Image.new("RGB", (600, 400), "#060609"); modulos.ficha_operador(a, r, pal, {"NAME": "CYBERDECK"})
    b = Image.new("RGB", (600, 400), "#060609"); modulos.ficha_operador(b, r, pal, {"NAME": "CYBERDECK"}, foto=Image.new("L", (300, 300), 255))
    assert a.tobytes() != b.tobytes()


def test_fonte_troca_para_japones_quando_ha_kanji():
    from poster import modulos
    assert modulos._fonte_para("TRACE ROUTE 経路追跡", "mono") == "dot"
    assert modulos._fonte_para("TRACE ROUTE", "mono") == "mono"
    assert modulos._fonte_para("↓1.2M ↑40K", "mono") == "dot"
    assert modulos._fonte_para("監視中", "cjk") == "cjk"


def test_dither_corta_em_vez_de_esticar():
    # foto em pé num retângulo largo: recorta o miolo mantendo a proporção (antes achatava a figura)
    src = Image.new("L", (100, 200), 0)
    src.paste(255, (0, 0, 100, 40))            # faixa branca só no topo da foto
    out = m.dither(src, Rect(0, 0, 200, 100), "#B8FF2E").convert("RGB")
    assert out.size == (200, 100)
    assert out.getpixel((100, 5)) == (6, 6, 9)  # esticada, o topo do retângulo seria a faixa branca


def test_dither_recorte_pode_mirar_embaixo():
    # foto da rua: o carro fica embaixo, o recorte precisa poder puxar para baixo
    src = Image.new("L", (100, 100), 0)
    src.paste(255, (0, 80, 100, 100))
    out = m.dither(src, Rect(0, 0, 200, 50), "#B8FF2E", centro=(0.5, 1.0)).convert("RGB")
    assert out.getpixel((100, 45)) == (184, 255, 46)


def test_placeholder_e_abstrato():
    import inspect
    fonte = inspect.getsource(m.placeholder_foto)
    assert "olho" not in fonte and "ellipse" not in fonte   # sem cabeça/olhos desenhados
