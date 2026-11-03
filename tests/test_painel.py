import paleta
from poster import modulos, painel

PAL = paleta.carregar("acid")
DADOS = {"hora": "18:07", "data": "SEG 26.10", "musica": "DOUDOU — A Rusty Dream", "progresso": 0.4,
         "ip": "10.0.0.16", "rede": "↓1.2M ↑40K", "temp": "cpu 46°C · gpu 47°C", "ia": "on qwen3:8b",
         "backup": "1h", "alertas": "ok"}


def test_tamanho_e_conteudo():
    im = painel.render(DADOS, PAL, (608, 968), 0)
    assert im.size == (608, 968)
    assert im.convert("L").getextrema()[1] > 100


def test_mostra_cyberdeck_hora_e_musica():
    modulos._LOG_TEXTOS.clear()
    painel.render(DADOS, PAL, (608, 968), 0)
    log = " ".join(modulos._LOG_TEXTOS)
    assert "CYBERDECK" in log and "18:07" in log and "A Rusty Dream" in log


def test_hora_diferente_muda_a_imagem():
    a = painel.render(DADOS, PAL, (608, 968), 0)
    b = painel.render({**DADOS, "hora": "18:08"}, PAL, (608, 968), 0)
    assert a.tobytes() != b.tobytes()


def test_sem_dados_nao_quebra():
    im = painel.render({}, PAL, (608, 968), 0)
    assert im.size == (608, 968)


def test_sem_texto_proibido():
    modulos._LOG_TEXTOS.clear()
    painel.render(DADOS, PAL, (608, 968), 3)
    log = " ".join(modulos._LOG_TEXTOS).lower()
    assert not any(t in log for t in modulos.TEXTOS_PROIBIDOS)


def test_tamanho_minusculo_nao_quebra():
    for tam in ((64, 64), (150, 300), (0, 0)):
        im = painel.render(DADOS, PAL, tam, 0)
        assert im.size[0] >= 1 and im.size[1] >= 1
