from pathlib import Path
import hashlib

import pytest

import layout
import paleta
from poster import compor

L = layout.carregar_layout(medido=None)
PAL = paleta.carregar("acid")


@pytest.fixture(scope="module")
def imgs():
    return {s: compor.compor(s, L, PAL, None).convert("RGB") for s in L.saidas()}


def _nao_fundo(img, caixa, passo=3):
    fundo = paleta.hex_rgb(PAL["fundo"])
    px = img.load()
    x0, y0, x1, y1 = caixa
    tot = n = 0
    for y in range(y0, y1, passo):
        for x in range(x0, x1, passo):
            tot += 1
            p = px[x, y]
            if max(abs(p[i] - fundo[i]) for i in range(3)) > 24:
                n += 1
    return n / max(tot, 1)


def test_tamanho(imgs):
    for s, im in imgs.items():
        assert im.size == L.tamanho(s)


def test_moldura_do_painel_no_topo(imgs):
    for im in imgs.values():
        assert _nao_fundo(im, (0, 0, im.width, L.painel), passo=2) > 0.02


def test_vaos_tem_arte(imgs):
    for s, im in imgs.items():
        rects = list(L.slots(s).values())
        # vão vertical entre o primeiro par de slots lado a lado
        a, b = sorted(rects, key=lambda r: r.x)[0], sorted(rects, key=lambda r: r.x)[-1]
        vao = (a.x + a.w, a.y, a.x + a.w + L.gap_interno, a.y + a.h)
        assert _nao_fundo(im, vao, passo=1) > 0.02, s


def test_conteudo_escondido_distinto_atras_de_cada_slot(imgs):
    hashes = set()
    for s, im in imgs.items():
        for nome, r in L.slots(s).items():
            caixa = (r.x, r.y, r.x + r.w, r.y + r.h)
            assert _nao_fundo(im, caixa) > 0.05, f"{s}:{nome} vazio"
            hashes.add(hashlib.md5(im.crop(caixa).resize((64, 64)).tobytes()).hexdigest())
    assert len(hashes) == sum(len(L.slots(s)) for s in L.saidas())


def _tem_cor_de_trilha(img, caixa):
    alvos = [paleta.hex_rgb(PAL[k]) for k in ("accent", "foco", "circuito")]
    px = img.load()
    x0, y0, x1, y1 = caixa
    return any(max(abs(px[x, y][i] - a[i]) for i in range(3)) < 30 for y in range(y0, y1) for x in range(x0, x1) for a in alvos)


def test_monitores_isolados_sem_trilha_na_divisa(imgs):
    faixa = (L.painel + 40, 1000)   # abaixo da moldura do painel
    assert not _tem_cor_de_trilha(imgs["HDMI-A-1"], (2556, faixa[0], 2560, faixa[1]))
    assert not _tem_cor_de_trilha(imgs["DP-3"], (0, faixa[0], 3, faixa[1]))


def test_gerar_pula_saida_desconectada(tmp_path):
    feitas = compor.gerar(["DP-3"], L, PAL, None, tmp_path)
    assert [s for s, _ in feitas] == ["DP-3"]
    assert len(list(tmp_path.glob("*.png"))) == 1


def test_sem_texto_proibido():
    from poster import modulos
    modulos._LOG_TEXTOS.clear()
    compor.compor("HDMI-A-1", L, PAL, None)
    compor.compor("DP-3", L, PAL, None)
    log = " ".join(modulos._LOG_TEXTOS).lower()
    assert log and not any(t in log for t in modulos.TEXTOS_PROIBIDOS)
    assert not any(app in log for app in ("brave", "spotify", "cava", "terminal.livre"))


def test_limpeza_nao_apaga_poster_em_uso(tmp_path):
    em_uso = tmp_path / "poster-DP-3-v1.png"; em_uso.write_bytes(b"x")
    velho = tmp_path / "poster-DP-3-v0.png"; velho.write_bytes(b"x")
    novo = tmp_path / "poster-DP-3-v2.png"; novo.write_bytes(b"x")
    compor.limpar_antigos(tmp_path, manter={em_uso, novo})
    assert em_uso.exists() and novo.exists() and not velho.exists()


def test_poster_nightcity_sem_accent_acid():
    nc = paleta.carregar("nightcity")
    im = compor.compor("DP-3", L, nc, None).convert("RGB").resize((480, 270))
    acid = paleta.hex_rgb(PAL["accent"])
    assert not any(max(abs(p[i] - acid[i]) for i in range(3)) < 20 for p in im.getdata())


def test_dossie_em_espaco_largo_poe_a_figura_ao_lado_com_altura_inteira():
    from PIL import Image
    r = layout.Rect(0, 0, 1308, 613)
    img = Image.new("RGB", (1308, 613), PAL["fundo"])
    compor._atras_terminal_livre(img, r, PAL, None, 1)
    foco = paleta.hex_rgb(PAL["foco"])
    caixa = img.crop((850, 60, 1200, 260)).getdata()   # no alto, onde antes ficava a ficha
    assert sum(p == foco for p in caixa) / len(caixa) > 0.15   # figura (roxa) em pé à direita, do topo até embaixo


def _fotos_cinza(tmp_path, nome):
    from PIL import Image
    Image.linear_gradient("L").resize((1600, 700)).save(tmp_path / f"{nome}.png")
    return tmp_path


def _fracao(img, caixa, cor):
    alvo = paleta.hex_rgb(PAL[cor])
    px = img.crop(caixa).getdata()
    return sum(p == alvo for p in px) / len(px)


@pytest.mark.parametrize("func,foto,caixa,cor", [
    (compor._atras_cava, "viaduto", (100, 40, 1200, 200), "foco"),            # faixa larga: foto no alto, de ponta a ponta
    (compor._atras_terminal_rapido, "mao", (60, 60, 420, 380), "accent"),     # foto na coluna da esquerda
])
def test_cava_e_hud_ganham_foto_quando_ela_existe(tmp_path, func, foto, caixa, cor):
    from PIL import Image
    r = layout.Rect(0, 0, 1302, 330) if foto == "viaduto" else layout.Rect(0, 0, 862, 462)
    sem, com = (Image.new("RGB", (r.w, r.h), PAL["fundo"]) for _ in range(2))
    func(sem, r, PAL, None, 1)
    func(com, r, PAL, _fotos_cinza(tmp_path, foto), 1)
    assert _fracao(com, caixa, cor) > 0.15 > _fracao(sem, caixa, cor)


def test_brave_rodape_tem_densidade():
    from PIL import Image
    r = layout.Rect(0, 0, 934, 952)
    img = Image.new("RGB", (r.w, r.h), PAL["fundo"])
    compor._atras_brave(img, r, PAL, None, 1)
    assert _nao_fundo(img, (560, 590, 900, 700), passo=2) > 0.10   # barras à direita do título
    assert _nao_fundo(img, (30, 820, 900, 930), passo=2) > 0.05    # microtexto fechando a base


def test_sem_camada_de_retrato_mesmo_com_retrato_na_pasta(tmp_path):
    # o pôster não tem camada de retrato: um retrato qualquer na pasta de fotos é ignorado
    from PIL import Image
    fotos = tmp_path / "fotos"
    fotos.mkdir()
    Image.new("L", (64, 64), 255).save(fotos / "face.png")
    a = compor.compor("HDMI-A-1", L, PAL, fotos)
    b = compor.compor("HDMI-A-1", L, PAL, None)
    from PIL import ImageChops
    assert ImageChops.difference(a, b).getbbox() is None


def test_assinatura_configuravel_aparece_no_poster(monkeypatch):
    from poster import modulos
    monkeypatch.setenv("CYBERDECK_SIGNATURE", "nodezero")
    modulos._LOG_TEXTOS.clear()
    compor.compor("HDMI-A-1", L, PAL, None)
    assert "NODEZERO" in modulos._LOG_TEXTOS


def test_brave_ntp_usa_o_monitor_do_brave():
    import gerar_poster
    assert gerar_poster.saida_do_brave(L, ["HDMI-A-1", "DP-3"]) == "DP-3"
    assert gerar_poster.saida_do_brave(L, ["HDMI-A-1"]) == "HDMI-A-1"
