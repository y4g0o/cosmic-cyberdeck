import gerar_placas as gp
import paleta

PAL = paleta.carregar("acid")
APP = ('<?xml version="1.0"?>\n<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
       'width="64" height="64" version="1.1" viewBox="0 0 16 16"><path d="M1 1h14v14H1z" fill="#B8FF2E"/></svg>\n')


def test_placa_envolve_o_simbolo_original_sem_perder_nada():
    out = gp.em_placa(APP, PAL)
    assert gp.MARCA in out
    assert '<path d="M1 1h14v14H1z" fill="#B8FF2E"/>' in out    # o desenho original, intacto
    assert 'transform="translate(8 8) scale(3) translate(0 0)"' in out   # 16 unidades -> 48 no centro
    assert 'xmlns:xlink="http://www.w3.org/1999/xlink"' in out   # namespaces do original continuam valendo
    assert 'width="64" height="64"' in out


def test_placa_nao_dobra_e_pula_svg_sem_tamanho():
    out = gp.em_placa(APP, PAL)
    assert gp.em_placa(out, PAL) is None                        # já tem placa
    assert gp.em_placa('<svg xmlns="http://www.w3.org/2000/svg"><g/></svg>', PAL) is None   # sem viewBox nem tamanho


def test_placa_usa_width_height_quando_falta_viewbox():
    out = gp.em_placa('<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48"><g/></svg>', PAL)
    assert "scale(1)" in out


def test_pasta_grande_tem_placa_simbolo_e_codigo_pequena_so_simbolo():
    grande = gp.pasta("folder-music", 64, PAL)
    pequena = gp.pasta("folder-music", 16, PAL)
    assert gp.MARCA in grande and "data:image/png;base64," in grande       # código como imagem embutida
    assert gp.SIMBOLOS["music"] in grande and gp.SIMBOLOS["music"] in pequena
    assert "data:image/png" not in pequena and "polygon" not in pequena    # sem placa nem kanji no tamanho pequeno


def test_pastas_diferentes_tem_simbolos_diferentes():
    assert len({gp.pasta(n, 48, PAL) for n in ("folder-documents", "folder-download", "folder-music")}) == 3


def test_numeros_do_svg_sem_menos_zero_e_com_sinal_certo():
    assert [gp._n(v) for v in (-0.0, 0.0, -3.5, -0.25, 12, 1.33333)] == ["0", "0", "-3.5", "-0.25", "12", "1.3333"]


FOLHA = ('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" version="1.1">\n'
         ' <path style="opacity:0.2" d="M 12.75,5 C 11.2265,5 10,6.2488 10,7.8 v 50.4 c 0,1.55008 1.2265,2.8 2.75,2.8 h 38.5 C 52.7724,61 54,59.75008 54,58.2 V 23 L 40,19 36,5 Z"/>\n'
         f' <path style="fill:#d0d1dd" d="{gp.FOLHA_PAPIRUS}"/>\n'
         ' <path style="opacity:0.2" d="M 54,23 36,5 V 20.1875 C 36,21.74675 37.2555,23 38.8125,23 Z"/>\n'
         ' <path style="fill:#e8eaf3" d="M 54,22 36,4 V 19.1875 C 36,20.74675 37.2555,22 38.8125,22 Z"/>\n'
         ' <path style="opacity:0.5" d="m 20,31 v 3 h 24 v -3 z"/>\n'
         ' <path style="fill:#ff4568" d="M 1 1 h 2 v 2 z"/>\n</svg>\n')


def test_ficha_troca_a_folha_clara_e_mantem_o_simbolo():
    out = gp.em_ficha(FOLHA, PAL)
    assert gp.MARCA in out and "#d0d1dd" not in out and "M 54,22 36,4" not in out and "M 12.75,5" not in out
    assert 'd="m 20,31 v 3 h 24 v -3 z"' in out and "#ff4568" in out           # símbolo do tipo intacto
    assert f'fill="{PAL["texto"]}"' in out                                       # linhas escuras viram claras
    assert gp.em_ficha(out, PAL) is None                                         # não dobra


def test_ficha_ignora_svg_sem_a_folha_do_papirus():
    assert gp.em_ficha('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><g/></svg>', PAL) is None


def test_ficha_clareia_traco_escuro_e_aceita_a_folha_compacta():
    log = FOLHA.replace('<path style="opacity:0.5" d="m 20,31 v 3 h 24 v -3 z"/>',
                        '<path style="opacity:0.5;fill:none;stroke:#0f0d18;stroke-width:2" d="m 10,41 12,0"/>')
    out = gp.em_ficha(log, PAL)
    assert "#0f0d18" not in out and f"stroke:{PAL['texto']}" in out           # linha do log aparece na ficha
    compacta = ('<svg width="64" height="64" xmlns="http://www.w3.org/2000/svg">'
                f'<path d="{gp.FOLHAS_PAPIRUS[1]}" style="fill:#8960ff"/><path d="m54 22-18-18v15z" style="fill:#fff"/>'
                '<path d="M1 1h2z" style="fill:#fff"/></svg>')
    out = gp.em_ficha(compacta, PAL)
    assert out and "#8960ff" in out and "m54 22-18-18" not in out               # borda na cor do tipo; dobra sai


def test_placa_leva_estilo_da_raiz_e_nao_confunde_stroke_width():
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" stroke-width="2" width="24" height="24" '
           'style="fill:#ff0000" fill="#00ff00"><path d="M0 0h1"/></svg>')
    out = gp.em_placa(svg, PAL)
    assert 'width="24" height="24"' in out and 'scale(2)' in out    # 24 -> 48, não confundiu com stroke-width
    g = out[out.index("<g transform"):]
    assert 'style="fill:#ff0000"' in g.split(">")[0] and 'fill="#00ff00"' in g.split(">")[0]


def test_tamanho_logico_das_pastas_2x():
    from pathlib import Path
    assert gp._tamanho(Path("16x16@2x")) == 16 and gp._tamanho(Path("64x64")) == 64


def test_simbolicos_da_barra_lateral_tem_desenho_angular_e_cores_da_paleta(tmp_path):
    for sub in ("16x16/symbolic/places", "16x16/symbolic/devices", "16x16/symbolic/actions"):
        (tmp_path / sub).mkdir(parents=True)
    gp.aplicar(tmp_path, PAL)
    home = (tmp_path / "16x16/symbolic/places/user-home-symbolic.svg").read_text()
    disco = (tmp_path / "16x16/symbolic/devices/drive-harddisk-symbolic.svg").read_text()
    recente = (tmp_path / "16x16/symbolic/actions/document-open-recent-symbolic.svg").read_text()
    assert gp.MARCA in home and PAL["accent"] in home and PAL["foco"] in home
    assert home != disco and disco != recente


def test_pastas_sem_kanji_e_com_codigo_de_arquivo():
    # estilo "etiqueta de arquivo": número // rótulo em fonte mono, nada de kanji
    import re
    for nome, (simbolo, codigo) in gp.PASTAS.items():
        assert not re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", codigo), nome
    assert gp.PASTAS["folder-documents"][1] == "01 // DOC" and gp.PASTAS["user-home"][1] == "00 // HOME"
    assert gp.pasta("folder-documents", 64, PAL) != gp.pasta("folder-download", 64, PAL)
