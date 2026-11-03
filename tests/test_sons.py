import numpy as np

import gerar_sons as gs


def test_todo_evento_e_curto_e_sem_estouro():
    for nome in gs.EVENTOS:
        onda = gs.sintetizar(nome)
        assert onda.dtype == np.float32
        assert 0.03 < len(onda) / gs.TAXA <= 0.6, nome
        assert np.abs(onda).max() <= gs.PICO + 1e-6, nome


def test_comeca_e_termina_em_silencio():
    # sem estalo: o envelope abre e fecha no zero
    for nome in gs.EVENTOS:
        onda = gs.sintetizar(nome)
        assert abs(onda[0]) < 1e-3 and abs(onda[-1]) < 1e-3, nome


def test_sons_diferentes_entre_si():
    a, b = gs.sintetizar("device-added"), gs.sintetizar("device-removed")
    assert len(a) != len(b) or not np.allclose(a, b)


def test_tema_herda_do_freedesktop():
    texto = gs.index_theme()
    assert "Inherits=freedesktop" in texto and "Directories=stereo" in texto


def test_sons_graves_e_macios():
    # a 1ª versão era aguda demais (energia em 5-12 kHz, chiado de onda quadrada e bitcrush)
    for nome in gs.EVENTOS:
        onda = gs.sintetizar(nome)
        e = np.abs(np.fft.rfft(onda))
        f = np.fft.rfftfreq(len(onda), 1 / gs.TAXA)
        assert (e * f).sum() / e.sum() < 1500, nome
