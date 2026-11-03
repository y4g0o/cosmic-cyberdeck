import re, subprocess, time, pathlib, json
import hud

ANSI = re.compile(r"\x1b\[[0-9;]*m")
PAL = {"fundo": "#060609", "accent": "#B8FF2E", "foco": "#7B4DFF", "roxo_profundo": "#2B1B6E",
       "circuito": "#3C7BFF", "alerta": "#FF2D55", "texto": "#E8EAF2"}
PROIBIDOS = ["cyberpunk", "2077", "edgerunner", "arasaka", "night city", "samurai", "militech"]


def boom(*a, **k):
    raise FileNotFoundError("x")


def timeout(*a, **k):
    raise TimeoutError("x")


class R:
    def __init__(self, out="", rc=0):
        self.stdout, self.returncode = out, rc


def run_ok(out):
    return lambda *a, **k: R(out)


COLETORES = [
    ("cpu", lambda d: hud.cpu(read=d, sleep=lambda s: None)),
    ("ram", lambda d: hud.ram(read=d)),
    ("gpu", lambda d: hud.gpu(run=d)),
    ("ollama", lambda d: hud.ollama(http_get=d)),
    ("rede", lambda d: hud.rede(read=d, sleep=lambda s: None)),
    ("disco", lambda d: hud.disco(usage=d)),
    ("backup", lambda d: hud.backup(run=d, unidade="restic-backup.service")),
    ("musica", lambda d: hud.musica(run=d)),
]


def test_coletores_nunca_levantam():
    for nome, f in COLETORES:
        for exc in (boom, timeout, lambda *a, **k: 1 / 0, lambda *a, **k: R("lixo\x00", 1)):
            r = f(exc)
            assert r in ("offline", "—") or isinstance(r, str), nome
            assert isinstance(r, str) and r, nome


def test_servico_ausente_offline_ou_traco():
    assert hud.gpu(run=boom) == "offline"
    assert hud.ollama(http_get=boom) == "offline"
    assert hud.musica(run=boom) == "—"
    assert hud.backup(run=boom, unidade="restic-backup.service") == "—"
    assert hud.backup(run=boom, unidade="") == "—"   # sem unidade configurada: escondido
    assert hud.cpu(read=boom, sleep=lambda s: None) == "—"


def test_cpu_delta():
    amostras = iter(["cpu  100 0 100 800 0 0 0 0 0 0\n", "cpu  150 0 150 900 0 0 0 0 0 0\n"])
    assert hud.cpu(read=lambda p: next(amostras), sleep=lambda s: None) == "50%"


def test_ram():
    mi = "MemTotal: 16000000 kB\nMemAvailable: 8000000 kB\n"
    assert hud.ram(read=lambda p: mi) == "7.6/15.3G"


def test_gpu():
    assert hud.gpu(run=run_ok("12, 45, 1024, 8188\n")) == "12% 45°C 1.0/8.0G"


def test_ollama():
    ps = json.dumps({"models": [{"name": "qwen3:8b"}]})
    assert hud.ollama(http_get=lambda u: ps) == "on qwen3:8b"
    assert hud.ollama(http_get=lambda u: '{"models": []}') == "on idle"


def test_rede():
    a = iter(["h\nh\n  lo: 1 0 0 0 0 0 0 0 1 0 0 0 0 0 0 0\neth0: 1000 0 0 0 0 0 0 0 2000 0 0 0 0 0 0 0\n",
              "h\nh\n  lo: 1 0 0 0 0 0 0 0 1 0 0 0 0 0 0 0\neth0: 3048 0 0 0 0 0 0 0 4048 0 0 0 0 0 0 0\n"])
    assert hud.rede(read=lambda p: next(a), sleep=lambda s: None) == "↓10.0K ↑10.0K"


def test_disco():
    U = type("U", (), {})
    u = U(); u.total, u.used, u.free = 100, 62, 38
    assert hud.disco(usage=lambda p: u) == "62%"


def test_backup():
    agora = time.mktime(time.strptime("2026-10-26 12:00", "%Y-%m-%d %H:%M"))
    out = "2026-10-26T03:00:01-0300 pc systemd[1]: Finished restic.\n"
    r = hud.backup(run=run_ok(out), unidade="restic-backup.service", agora=lambda: hud.datetime.fromisoformat("2026-10-26T12:00:01-03:00").timestamp())
    assert r == "9h"
    r = hud.backup(run=run_ok(out), unidade="restic-backup.service", agora=lambda: hud.datetime.fromisoformat("2026-10-29T03:00:01-03:00").timestamp())
    assert r == "3d"
    assert hud.backup(run=run_ok("-- No entries --\n"), unidade="restic-backup.service") == "—"


def test_musica_playerctl_e_gdbus():
    assert hud.musica(run=run_ok("Daft Punk — Around\n")) == "Daft Punk — Around"

    def run(cmd, **k):
        if cmd[0] == "playerctl":
            raise FileNotFoundError
        return R("(<{'xesam:artist': <['Boards of Canada']>, 'xesam:title': <\"Roygbiv's\">}>,)\n")
    assert hud.musica(run=run) == "Boards of Canada — Roygbiv's"


def test_alertas():
    base = {"disco": "50%", "gpu": "10% 50°C 1.0/8.0G", "backup": "5h"}
    assert hud.alertas(base) == "ok"
    assert "disco" in hud.alertas({**base, "disco": "95%"})
    assert "gpu" in hud.alertas({**base, "gpu": "10% 85°C 1.0/8.0G"})
    assert "backup" in hud.alertas({**base, "backup": "3d"})
    assert hud.alertas({"disco": "—", "gpu": "offline", "backup": "—"}) == "ok"


DADOS = {"cpu": "12%", "ram": "7.6/15.3G", "gpu": "12% 45°C 1.0/8.0G", "ollama": "on qwen3:8b",
         "rede": "↓10.0K ↑10.0K", "disco": "62%", "backup": "9h",
         "musica": "Daft Punk — Around the World — Extended Mix Very Long Title Here", "alertas": "ok"}


def test_render_cabe_e_conteudo():
    for larg in (20, 40, 60, 100):
        out = hud.render(DADOS, PAL, larg)
        plano = ANSI.sub("", out)
        for linha in plano.split("\n"):
            assert len(linha) <= larg, (larg, linha)
        assert "\x1b[38;2;" in out
    plano = ANSI.sub("", hud.render(DADOS, PAL, 60))
    assert "cyberdeck" in plano
    for rot in ("SYS", "VRAM", "IA", "NET", "DISK", "♪", "ICE"):
        assert rot in plano
    assert re.search(r"[ｦ-ﾝ]", plano) and "0" in plano
    low = plano.lower()
    for p in PROIBIDOS:
        assert p not in low


def test_render_dados_vazios():
    plano = ANSI.sub("", hud.render({}, PAL, 50))
    assert "cyberdeck" in plano and "—" in plano


def test_uma_vez_rapido_tudo_simulado(capsys):
    t = time.time()
    hud.main(["--uma-vez"], coletar=lambda: DADOS, pal=PAL, largura=60)
    assert time.time() - t < 1.5
    assert "cyberdeck" in ANSI.sub("", capsys.readouterr().out)


def test_coletar_tudo_com_falhas_nao_levanta():
    d = hud.coletar(run=boom, http_get=boom, read=boom, usage=boom, sleep=lambda s: None)
    assert set(d) >= {"cpu", "ram", "gpu", "ollama", "rede", "disco", "backup", "musica", "alertas"}
    assert d["gpu"] == "offline" and d["ollama"] == "offline"


def test_painel_ansi_desenha_no_topo_e_restaura_cursor():
    import hud
    s = hud.painel_ansi("linha 1\nlinha 2")
    assert s.startswith("\x1b7") and s.endswith("\x1b8")
    assert "\x1b[1;1H" in s and s.count("\x1b[2K") == 2


def test_linhas_do_hud_conta_o_render():
    import hud
    dados = {k: "—" for k in ("cpu", "ram", "gpu", "ollama", "rede", "disco", "backup", "musica", "alertas")}
    n = len(hud.render(dados, hud._paleta(), 60).splitlines())
    assert hud.linhas_do_painel(dados, 60) == n


def test_painel_reaplica_regiao_de_rolagem_a_cada_ciclo():
    import hud
    s = hud.painel_ansi("a\nb\nc", linhas_terminal=40)
    assert "\x1b[4;40r" in s and s.startswith("\x1b7") and s.endswith("\x1b8")


def test_hud_so_desenha_com_o_shell_em_primeiro_plano():
    # no prompt o grupo em primeiro plano é o do shell; com um programa rodando (claude, less...) é outro
    assert hud.shell_em_primeiro_plano(1, 500, tcgetpgrp=lambda fd: 500, getpgid=lambda pid: 500)
    assert not hud.shell_em_primeiro_plano(1, 500, tcgetpgrp=lambda fd: 777, getpgid=lambda pid: 500)


def test_hud_troca_de_paleta_quando_o_arquivo_ativa_muda():
    carregou = []
    nova = lambda: carregou.append(1) or {"accent": "#000000"}
    assert hud.paleta_atual(PAL, 10.0, 10.0, nova) == (PAL, 10.0)
    assert hud.paleta_atual(PAL, 10.0, 11.0, nova) == ({"accent": "#000000"}, 11.0)
    assert carregou == [1]


def test_hud_duas_colunas_barras_sparkline_top_e_progresso_musica():
    assert hud.musica(run=run_ok("Daft Punk — Around\t60000000\t180000000\n")).endswith("01:00 ━━●─── 03:00")
    assert hud.top_proc(run=run_ok("ps 0.0\ncosmic-comp 4.2\n")) == "cosmic-comp 4.2%"
    plano = ANSI.sub("", hud.render({**DADOS, "top": "cosmic-comp 4.2%"}, PAL, 92))
    assert "┏━━" in plano and "┗━━" in plano and "│" in plano
    assert "▰" in plano and "top: cosmic-comp 4.2%" in plano


def test_cockpit_braille_agentes_git_e_notas(tmp_path):
    s = hud._braille_spark([10, 40, 80, 100, 50, 20], largura_chars=3)
    assert len(s) == 3 and all(0x2800 <= ord(c) <= 0x28FF for c in s)
    ps_out = (
        "100 1 0.2 /opt/u/.local/share/claude/versions/2.1.312\n"
        "200 1 1.0 /opt/u/.local/bin/agy\n"
        "201 200 45.0 pytest -q\n"
        "300 1 0.1 node /opt/u/.local/share/fnm/aliases/default/bin/opencode\n"
    )
    ag = hud.agentes(run=run_ok(ps_out))
    assert "claude: ● PRONTO" in ag and "agy: ⚡ ATIVO (pytest)" in ag and "opencode: ● PRONTO" in ag
    arq = tmp_path / "notas.json"
    assert "Adicionada [1]" in hud.gerenciar_notas(["Testar", "reboot"], arq)
    assert "[1] Testar reboot" in hud.gerenciar_notas(["-l"], arq)
    assert "Concluída: Testar reboot" in hud.gerenciar_notas(["-d", "1"], arq)
    assert hud.carregar_notas(arq) == []
    arq_c = tmp_path / "cmds.json"
    assert "Comando salvo" in hud.gerenciar_cmds(["add", "meu-cmd", "faz algo util"], PAL, arq_c)
    painel_c = ANSI.sub("", hud.gerenciar_cmds(["meu-cmd"], PAL, arq_c))
    assert "meu-cmd" in painel_c and "faz algo util" in painel_c


def test_notas_ficam_fora_do_cache():
    assert ".cache" not in str(hud.ARQ_NOTAS) and hud.ARQ_NOTAS.name == "notas.json"


def test_docker_lista_containers_esquecidos():
    assert hud.docker(run=run_ok("")) == "—"
    out = hud.docker(run=run_ok("postgres\tUp 2 hours\nredis\tUp About a minute\nx\tUp 9 seconds\n"))
    assert out == "◆ postgres 2h  ◆ redis 1m  ◆ x <1m"
    assert hud.docker(run=boom) == "—" and hud.docker(run=lambda *a, **k: R("", 1)) == "—"


def test_linha_dock_so_aparece_com_container_aberto():
    com = ANSI.sub("", hud.render({**DADOS, "docker": "◆ postgres 2h"}, PAL, 92))
    assert "DOCK" in com and "◆ postgres 2h" in com and "1 aberto" in com
    assert "DOCK" in ANSI.sub("", hud.render({**DADOS, "docker": "◆ postgres 2h"}, PAL, 40))   # layout estreito também
    for vazio in ("—", ""):
        assert "DOCK" not in ANSI.sub("", hud.render({**DADOS, "docker": vazio}, PAL, 92))
    assert "dock:" not in com                                                    # saiu da célula ICE


def test_radar_git_inclui_este_repositorio_e_os_do_config():
    nomes = [n for n, _ in hud._repos_padrao()]
    assert nomes[0] == "cyberdeck"
    assert hud._repos_padrao()[0][1] == hud.RAIZ


def test_catalogo_sem_comandos_pessoais():
    texto = ANSI.sub("", hud.gerenciar_cmds([], PAL, pathlib.Path("/nao/existe.json")))
    assert "COMMAND DECK" in texto and "install.py --uninstall" in texto
