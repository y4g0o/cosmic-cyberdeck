import painel_dados as pd


def test_progresso_da_musica():
    pos = "(<int64 90000000>,)"                     # 90 s
    meta = "({'mpris:length': <uint64 240000000>, 'xesam:title': <'X'>},)"  # 240 s
    assert abs(pd.progresso(pos, meta) - 0.375) < 1e-6


def test_progresso_sem_spotify():
    assert pd.progresso("", "") == 0.0


def test_temperatura_cpu_lida_do_hwmon():
    arquivos = {"/sys/class/hwmon/hwmon2/name": "coretemp\n", "/sys/class/hwmon/hwmon2/temp1_input": "46500\n"}
    assert pd.temp_cpu(glob=lambda p: ["/sys/class/hwmon/hwmon2/name"], ler=lambda p: arquivos[p]) == "46°C"


def test_temperatura_cpu_ausente():
    assert pd.temp_cpu(glob=lambda p: [], ler=lambda p: "") == "—"


def test_temperatura_da_gpu_do_hud():
    assert pd.temp_gpu("12% 45°C 1.0/8.0G") == "45°C"
    assert pd.temp_gpu("offline") == "—"


def test_ip_local_sem_rede():
    def quebra(*a, **k):
        raise OSError
    assert pd.ip_local(quebra) == "—"
