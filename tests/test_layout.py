from pathlib import Path
import layout
from layout import Rect

L = layout.carregar_layout(medido=None)


def _sobrepoe(a: Rect, b: Rect) -> bool:
    return a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h


def test_saidas():
    assert set(L.saidas()) == {"HDMI-A-1", "DP-3"}
    assert L.tamanho("HDMI-A-1") == (2560, 1080)
    assert L.tamanho("DP-3") == (1920, 1080)


def test_nomes_dos_slots_e_zonas():
    assert set(L.slots("HDMI-A-1")) == {"terminal_livre", "spotify", "cava"}
    assert set(L.slots("DP-3")) == {"brave", "hud", "arquivos"}
    assert L.zonas("HDMI-A-1") == {}


def test_slots_dentro_da_tela_e_abaixo_do_painel():
    for s in L.saidas():
        w, h = L.tamanho(s)
        for r in list(L.slots(s).values()) + list(L.zonas(s).values()):
            assert r.x >= 0 and r.y >= L.painel and r.x + r.w <= w and r.y + r.h <= h


def test_sem_sobreposicao_e_com_vao():
    for s in L.saidas():
        rs = list(L.slots(s).values()) + list(L.zonas(s).values())
        for i, a in enumerate(rs):
            for b in rs[i + 1:]:
                assert not _sobrepoe(a, b)
                dx = max(b.x - (a.x + a.w), a.x - (b.x + b.w))
                dy = max(b.y - (a.y + a.h), a.y - (b.y + b.h))
                assert max(dx, dy) >= L.gap_interno


def test_divisoes_contra_o_lado_mais_longo_sao_giradas():
    # o COSMIC divide pelo lado mais longo; onde a árvore pede o contrário, o cyberdeck gira com Super+O
    import montar
    assert montar.giros(L, "HDMI-A-1") == {"cava"}    # Spotify em cima do cava numa metade larga
    assert montar.giros(L, "DP-3") == set()


def test_ultrawide_spotify_em_cima_do_cava_e_terminal_a_direita():
    s = L.slots("HDMI-A-1")
    tl, sp, cv = s["terminal_livre"], s["spotify"], s["cava"]
    assert tl.h > 900 and tl.x > sp.x + sp.w
    assert cv.x == sp.x and cv.y > sp.y + sp.h and sp.w > 1000


def test_brave_a_esquerda_do_principal_com_altura_inteira():
    s = L.slots("DP-3")
    assert s["brave"].x <= L.gap_externo + L.gap_interno and s["brave"].h > 900
    assert s["hud"].x == s["arquivos"].x > s["brave"].x + s["brave"].w


def test_saidas_conectadas_sem_ultrawide():
    saida = "DP-3 (enabled)\n  Position: 2560,0\nHDMI-A-1 (disabled)\n"
    assert layout.saidas_conectadas(lambda: saida) == ["DP-3"]


def test_saidas_conectadas_falha_no_comando():
    def quebra():
        raise FileNotFoundError
    assert layout.saidas_conectadas(quebra) == []


def test_retangulos_batem_com_o_cosmic_medido():
    # modelo conferido ao vivo no COSMIC 1.11 com gaps (16, 24), (24, 36), (20, 28) e (8, 28); com os atuais
    # (0, 28) o COSMIC pôs as janelas em 28,60, altura total 992 e as empilhadas com 482, como o modelo dá
    esperado = {
        "DP-3": {"brave": Rect(28, 60, 918, 992), "hud": Rect(974, 60, 918, 482),
                 "arquivos": Rect(974, 570, 918, 482)},
    }
    for s, rects in esperado.items():
        assert {**L.slots(s), **L.zonas(s)} == rects


def test_medido_substitui_os_retangulos_da_arvore(tmp_path):
    arq = tmp_path / "medido.toml"
    layout.salvar_medido({"HDMI-A-1": {"terminal_livre": Rect(40, 72, 1148, 968), "spotify": Rect(1212, 72, 1308, 613),
                                       "cava": Rect(1212, 709, 1308, 331)}}, arq)
    M = layout.carregar_layout(medido=arq)
    assert M.slots("HDMI-A-1")["spotify"] == Rect(1212, 72, 1308, 613)
    assert M.tem_medido("HDMI-A-1") and not M.tem_medido("DP-3")
    assert M.slots("DP-3") == L.slots("DP-3")


def test_salvar_medido_mantem_as_outras_saidas(tmp_path):
    arq = tmp_path / "medido.toml"
    layout.salvar_medido({"DP-3": {"brave": Rect(40, 72, 1200, 968)}}, arq)
    layout.salvar_medido({"HDMI-A-1": {"spotify": Rect(1, 2, 3, 4)}}, arq)
    M = layout.carregar_layout(medido=arq)
    assert M.tem_medido("DP-3") and M.tem_medido("HDMI-A-1")


def test_medido_com_slot_que_nao_existe_mais_e_ignorado(tmp_path):
    arq = tmp_path / "medido.toml"
    layout.salvar_medido({"HDMI-A-1": {"arte": Rect(1, 2, 3, 4)}}, arq)
    assert not layout.carregar_layout(medido=arq).tem_medido("HDMI-A-1")


def test_posicoes_dos_monitores():
    saida = "HDMI-A-1 (enabled)\n  Position: 0,288\nDP-3 (enabled)\n  Position: 2560,0\nX (disabled)\n  Position: 9,9\n"
    assert layout.posicoes(lambda: saida) == {"HDMI-A-1": (0, 288), "DP-3": (2560, 0)}
    assert layout.posicoes(lambda: (_ for _ in ()).throw(FileNotFoundError)) == {}


def test_posicoes_com_a_saida_real_do_cosmic_randr_1_11():
    # o 1.11 pôs Make/Model/Physical Size entre o nome e a Position (e cores ANSI)
    texto = (Path(__file__).parent / "dados/cosmic-randr-1.11.txt").read_text()
    assert layout.posicoes(lambda: texto) == {"HDMI-A-1": (0, 288), "DP-3": (2560, 0)}


def test_mudar_vao_externo_estica_so_as_janelas_da_borda():
    # vão externo 20 -> 8: quem encosta na borda ganha 12 px para aquele lado; as divisórias ficam onde estão
    medido = {"brave": Rect(48, 80, 934, 952), "hud": Rect(1010, 80, 862, 462), "arquivos": Rect(1010, 570, 862, 462)}
    novo = layout.esticar_para_as_bordas(medido, largura=1920, altura=1080, painel=32, interno=28, antigo=20, novo=8)
    assert novo == {"brave": Rect(36, 68, 946, 976), "hud": Rect(1010, 68, 874, 474),
                    "arquivos": Rect(1010, 570, 874, 474)}
