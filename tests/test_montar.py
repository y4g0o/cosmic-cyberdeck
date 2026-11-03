import layout
import montar

L = layout.carregar_layout(medido=None)
TODAS = ["HDMI-A-1", "DP-3"]


def _seq(acoes):
    return [(a.tipo, a.slot, a.saida, a.foco) for a in acoes]


def test_ordem_de_insercao_segue_a_arvore():
    assert montar.ordem_insercao(L.arvore("HDMI-A-1")) == [
        ("spotify", None), ("terminal_livre", "spotify"), ("cava", "spotify")]
    assert montar.ordem_insercao(L.arvore("DP-3")) == [
        ("brave", None), ("hud", "brave"), ("arquivos", "hud")]


def test_area_vazia_abre_tudo_na_ordem():
    acoes = montar.plano_abertura(L, existentes=set(), no_lugar=set(), saidas=TODAS)
    assert _seq(acoes) == [
        ("abrir", "spotify", "HDMI-A-1", None), ("abrir", "terminal_livre", "HDMI-A-1", "spotify"),
        ("abrir", "cava", "HDMI-A-1", "spotify"),
        ("abrir", "brave", "DP-3", None), ("abrir", "hud", "DP-3", "brave"),
        ("abrir", "arquivos", "DP-3", "hud")]


def test_app_ja_aberto_e_movido_nao_reaberto():
    acoes = montar.plano_abertura(L, existentes={"spotify", "brave"}, no_lugar=set(), saidas=TODAS)
    tipos = {a.slot: a.tipo for a in acoes}
    assert tipos["spotify"] == "mover" and tipos["brave"] == "mover"
    assert tipos["terminal_livre"] == "abrir"


def test_rodar_de_novo_com_tudo_no_lugar_nao_faz_nada():
    todos = {"spotify", "terminal_livre", "cava", "brave", "hud", "arquivos"}
    assert montar.plano_abertura(L, existentes=todos, no_lugar=todos, saidas=TODAS) == []


def test_saida_ausente_so_monta_a_outra():
    acoes = montar.plano_abertura(L, existentes=set(), no_lugar=set(), saidas=["DP-3"])
    assert {a.saida for a in acoes} == {"DP-3"}


def test_montagem_parcial_retira_antes_e_nunca_fecha():
    acoes = montar.plano_abertura(L, existentes={"cava"}, no_lugar={"cava"}, saidas=TODAS)
    seq = _seq(acoes)
    assert ("retirar", "cava", "HDMI-A-1", None) in seq
    assert seq.index(("retirar", "cava", "HDMI-A-1", None)) < seq.index(("mover", "cava", "HDMI-A-1", "spotify"))
    assert all(a.tipo in ("abrir", "mover", "retirar") for a in acoes)


def test_cada_slot_tem_app_conhecido():
    for s in TODAS:
        for nome in list(L.slots(s)) + list(L.zonas(s)):
            assert nome in montar.APPS


def test_janela_intrusa_na_area_forca_remontagem():
    todos = {"spotify", "terminal_livre", "cava", "brave", "hud", "arquivos"}
    acoes = montar.plano_abertura(L, existentes=todos, no_lugar=todos, saidas=TODAS, intrusos={"DP-3"})
    assert {a.saida for a in acoes} == {"DP-3"}
    assert ("retirar", "brave", "DP-3", None) in _seq(acoes)


def test_janelas_fora_de_posicao_sao_detectadas():
    s = L.slots("HDMI-A-1")
    certas = {n: (r.x, r.y, r.w, r.h) for n, r in s.items()}
    assert not montar.desalinhada(L, "HDMI-A-1", certas)
    trocadas = {**certas, "spotify": certas["terminal_livre"], "terminal_livre": certas["spotify"]}
    assert montar.desalinhada(L, "HDMI-A-1", trocadas)
    assert not montar.desalinhada(L, "HDMI-A-1", {"spotify": None})  # sem geometria ainda: não acusa


class _CFalso:
    def __init__(self, areas, janelas):
        self._areas, self.janelas = areas, janelas

    def areas_da_saida(self, saida):
        return self._areas


def test_area_do_cyberdeck_reconhecida_pelo_app_do_slot_sem_titulo_cyberdeck():
    # principal só com o Brave: a área dele é a do cyberdeck, não a vazia do final
    c = _CFalso(["a1", "a2", "a3"], {1: {"app_id": "com.system76.CosmicTerm", "titulo": "outro", "areas": {"a1"}},
                                     2: {"app_id": "brave-browser", "titulo": "Brave", "areas": {"a2"}}})
    assert montar._area_do_layout(c, "DP-3", L) == "a2"
    assert montar._area_do_layout(_CFalso(["a1", "a2"], {}), "DP-3", L) == "a2"


def test_terminal_livre_reconhecido_na_area_mesmo_com_titulo_trocado():
    term = {"app_id": "com.system76.CosmicTerm", "titulo": "✳ nvim — Terminal"}
    assert montar.e_do_slot("terminal_livre", term, na_area=True)
    assert not montar.e_do_slot("terminal_livre", term, na_area=False)   # fora da área: não rouba outro terminal
    for outro in ("cava — Terminal", "cyberdeck:hud — Terminal", "cyberdeck:cava — Terminal"):
        assert not montar.e_do_slot("terminal_livre", {**term, "titulo": outro}, na_area=True)


def test_layout_medido_a_mao_nao_e_desalinhado(tmp_path):
    arq = tmp_path / "medido.toml"
    layout.salvar_medido({"HDMI-A-1": {"terminal_livre": layout.Rect(40, 72, 1148, 968)}}, arq)
    M = layout.carregar_layout(medido=arq)
    assert not montar.desalinhada(M, "HDMI-A-1", {"terminal_livre": (40, 72, 1228, 968)})


R = layout.Rect
ARV = ("H", ["terminal_livre", ("V", ["spotify", "cava"])])
ALVO = {"terminal_livre": R(60, 92, 1123, 928), "spotify": R(1219, 92, 1281, 584), "cava": R(1219, 712, 1281, 308)}


def test_ajuste_comeca_pela_divisoria_de_cima_da_arvore():
    metades = {"terminal_livre": R(60, 92, 1202, 928), "spotify": R(1298, 92, 1202, 446), "cava": R(1298, 574, 1202, 446)}
    # terminal largo demais: quem cresce é o vizinho do outro lado da divisória, para a esquerda
    assert montar.proximo_ajuste(ARV, metades, ALVO) in (("spotify", "left"), ("cava", "left"))


def test_ajuste_cresce_o_lado_de_baixo_ou_o_de_cima():
    raiz_ok = {"terminal_livre": ALVO["terminal_livre"], "spotify": R(1219, 92, 1281, 446), "cava": R(1219, 574, 1281, 446)}
    assert montar.proximo_ajuste(ARV, raiz_ok, ALVO) == ("spotify", "down")
    passou = {**raiz_ok, "spotify": R(1219, 92, 1281, 640), "cava": R(1219, 768, 1281, 252)}
    assert montar.proximo_ajuste(ARV, passou, ALVO) == ("cava", "up")


def test_ajuste_para_dentro_da_tolerancia():
    quase = {**ALVO, "spotify": R(1219, 92, 1281, 589), "cava": R(1219, 717, 1281, 303)}
    assert montar.proximo_ajuste(ARV, quase, ALVO) is None
    assert montar.proximo_ajuste(ARV, ALVO, ALVO) is None


def test_com_tamanhos_gravados_ordem_trocada_e_desalinhada(tmp_path):
    from layout import Rect, salvar_medido, carregar_layout
    arq = tmp_path / "medido.toml"
    salvar_medido({"HDMI-A-1": {"spotify": Rect(48, 80, 1302, 594), "cava": Rect(48, 702, 1302, 330),
                                "terminal_livre": Rect(1378, 80, 1134, 952)}}, arq)
    M = carregar_layout(medido=arq)
    certo = {"spotify": (48, 80, 1297, 594), "cava": (48, 702, 1297, 330), "terminal_livre": (1373, 80, 1139, 952)}
    trocado = {"terminal_livre": (48, 80, 1134, 952), "spotify": (1210, 80, 1302, 594), "cava": (1210, 702, 1302, 330)}
    assert not montar.desalinhada(M, "HDMI-A-1", certo)   # poucos pixels: o ajuste fino resolve
    assert montar.desalinhada(M, "HDMI-A-1", trocado)     # lado trocado: precisa remontar


def test_terminal_comum_no_principal_e_intruso():
    # o slot terminal_livre só existe no ultrawide: no principal um terminal sem papel atrapalha o tiling
    term = {"app_id": "com.system76.CosmicTerm", "titulo": "~ — Terminal", "areas": {"a1"}}
    hud = {"app_id": "com.system76.CosmicTerm", "titulo": "cyberdeck:hud — Terminal", "areas": {"a1"}}
    c = _CFalso(["a1"], {1: term, 2: hud})
    assert montar.intrusos_na_area(c, "DP-3", "a1", L) == [1]
    assert montar.intrusos_na_area(c, "HDMI-A-1", "a1", L) == [2]


def test_so_grava_sobra_pequena():
    from layout import Rect
    arv = L.arvore("DP-3")
    alvo = {"brave": Rect(48, 80, 934, 952), "hud": Rect(1010, 80, 862, 462), "arquivos": Rect(1010, 570, 862, 462)}
    perto = {"brave": Rect(48, 80, 939, 952), "hud": Rect(1015, 80, 857, 462), "arquivos": Rect(1015, 570, 857, 462)}
    torto = {"brave": Rect(1342, 80, 530, 462), "hud": Rect(1342, 570, 258, 462), "arquivos": Rect(1628, 570, 244, 462)}
    assert montar.sobra_pequena(arv, perto, alvo)
    assert not montar.sobra_pequena(arv, alvo, alvo)    # bate exato: nada a gravar
    assert not montar.sobra_pequena(arv, torto, alvo)   # montagem errada: nunca gravar por cima


def test_cursor_empurrado_para_dentro_do_monitor_mesmo_com_desnivel():
    pos = {"HDMI-A-1": (0, 288), "DP-3": (2560, 0)}
    assert montar.empurrao(pos, "HDMI-A-1") == (-300, 300)   # esquerda e para baixo: o ultrawide começa 288 px abaixo
    assert montar.empurrao(pos, "DP-3") == (300, -300)
    assert montar.empurrao({"A": (0, 0), "B": (1920, 0)}, "A") == (-300, 0)


def test_brave_abre_direto_no_perfil_padrao():
    # sem isso o Brave abre na tela de escolher perfil, o cyberdeck encaixa essa janela e a de verdade cai fora do lugar
    assert "--profile-directory=Default" in montar.APPS["brave"]["cmd"]


class _CChegando:
    """Janela anunciada sem geometria; ela chega e se acomoda alguns ciclos depois."""
    def __init__(self, geoms):
        self.janelas, self._geoms = {}, list(geoms)

    def atualizar(self, ciclos=1, espera=0):
        g = self._geoms.pop(0) if self._geoms else self.janelas[1]["geom"]
        self.janelas[1] = {"app_id": "brave-browser", "titulo": "", "areas": {"a1"} if g else set(), "geom": g}


def test_esperar_so_devolve_janela_ja_posicionada_e_parada():
    c = _CChegando([None, None, ("DP-3", 0, 0, 800, 600), ("DP-3", 48, 80, 900, 952), ("DP-3", 48, 80, 900, 952)])
    h = montar._esperar(c, lambda j: j["app_id"] == "brave-browser", set(), segundos=5)
    assert h == 1 and c.janelas[1]["geom"] == ("DP-3", 48, 80, 900, 952) and not c._geoms


def test_direcao_da_divisao_de_cada_giro():
    assert montar.direcao_do_giro(L.arvore("HDMI-A-1"), "cava") == "V"
    assert montar.direcao_do_giro(L.arvore("DP-3"), "arquivos") == "V"
    assert montar.direcao_do_giro(L.arvore("DP-3"), "brave") is None   # 1ª folha: não divide nada


def test_girou_certo_confere_o_lado_da_janela_nova():
    from layout import Rect
    sp = Rect(48, 80, 1302, 462)
    assert montar.girou_certo("V", sp, Rect(48, 570, 1302, 462))        # cava embaixo do Spotify
    assert not montar.girou_certo("V", Rect(48, 80, 630, 952), Rect(706, 80, 644, 952))   # ao lado: não girou
    assert montar.girou_certo("H", Rect(48, 80, 630, 952), Rect(706, 80, 644, 952))


def test_tudo_fechado_menos_o_terminal_monta_em_volta_dele():
    # fechou tudo e ficou só o terminal em uso: a área dele é a do cyberdeck (senão abre outro terminal em área vazia)
    term = {"app_id": "com.system76.CosmicTerm", "titulo": "✳ nvim — Terminal", "areas": {"a1"}}
    assert montar._area_do_layout(_CFalso(["a1", "a2"], {1: term}), "HDMI-A-1", L) == "a1"
    hud = {**term, "titulo": "cyberdeck:hud — Terminal"}   # terminal com papel não conta como terminal livre
    assert montar._area_do_layout(_CFalso(["a1", "a2"], {1: hud}), "HDMI-A-1", L) == "a2"


def test_terminal_em_uso_vence_area_posterior_com_outros_slots():
    term = {"app_id": "com.system76.CosmicTerm", "titulo": "✳ nvim — Terminal", "areas": {"a1"}}
    sp = {"app_id": "spotify", "titulo": "Spotify", "areas": {"a2"}}
    assert montar._area_do_layout(_CFalso(["a1", "a2", "a3"], {1: term, 2: sp}), "HDMI-A-1", L) == "a1"


class _CAnimando:
    """O atalho só faz efeito alguns ciclos depois: antes disso as leituras repetem o estado antigo."""
    def __init__(self, geoms):
        self._geoms = list(geoms)
        self.janelas = {1: {"geom": self._geoms[0]}}

    def atualizar(self, ciclos=1, espera=0):
        if len(self._geoms) > 1:
            self._geoms.pop(0)
        self.janelas[1]["geom"] = self._geoms[0]


def test_parado_espera_o_atalho_fazer_efeito_antes_de_julgar():
    from layout import Rect
    antes, depois = ("H", 48, 80, 588, 952), ("H", 48, 80, 1302, 462)
    c = _CAnimando([antes, antes, antes, antes, depois, depois, depois])
    r = montar._parado(c, {"cava": 1}, segundos=5, de={"cava": Rect(*antes[1:])})
    assert r == {"cava": Rect(*depois[1:])}


def test_erro_vai_para_o_log_e_sai_com_1(monkeypatch, capsys):
    def quebra(argv):
        raise KeyError("janela fechou no meio")
    monkeypatch.setattr(montar, "_main", quebra)
    assert montar._rodar([], trava=None) == 1
    assert "KeyError" in capsys.readouterr().err


def test_so_um_cyberdeck_por_vez(tmp_path):
    arq = tmp_path / "cyberdeck.lock"
    primeira = montar._travar(arq)
    assert primeira is not None and montar._travar(arq) is None   # 2º Super+Y enquanto o 1º roda: sai
    primeira.close()
    assert montar._travar(arq) is not None


def test_area_com_mais_janelas_do_layout_vence_terminal_solto():
    # layout montado na área 3; um terminal comum aberto na 1 não pode puxar tudo para lá
    term = {"app_id": "com.system76.CosmicTerm", "titulo": "~ — Terminal", "areas": {"a1"}}
    sp = {"app_id": "spotify", "titulo": "Spotify", "areas": {"a3"}}
    cv = {"app_id": "com.system76.CosmicTerm", "titulo": "cyberdeck:cava — Terminal", "areas": {"a3"}}
    assert montar._area_do_layout(_CFalso(["a1", "a2", "a3"], {1: term, 2: sp, 3: cv}), "HDMI-A-1", L) == "a3"


def test_segundo_cyberdeck_nao_apaga_o_log_do_que_esta_rodando(tmp_path):
    log, trava = tmp_path / "cyberdeck.log", tmp_path / "cyberdeck.lock"
    log.write_text("linhas do cyberdeck que está rodando\n")
    preso = montar._travar(trava)
    assert montar._rodar(["--log", str(log)], trava=trava) == 0
    assert log.read_text().startswith("linhas do cyberdeck que está rodando")
    preso.close()


def test_rects_ignora_janela_que_fechou_no_meio():
    class C:
        janelas = {1: {"geom": ("H", 1, 2, 3, 4)}}
    assert montar._rects(C(), {"a": 1, "b": 99}) == {"a": montar.layout.Rect(1, 2, 3, 4)}
