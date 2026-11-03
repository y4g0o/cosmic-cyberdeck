import re
from pathlib import Path

import pytest

import aplicar
import paleta

RAIZ = Path(__file__).resolve().parent.parent
NIGHTCITY = ["FCEE0A", "00F0FF", "FF003C", "252, 238, 10", "252,238,10", "0, 240, 255", "0,240,255"]
ACID = ["B8FF2E", "7B4DFF", "184, 255, 46", "184,255,46", "123, 77, 255", "123,77,255"]


def test_renderizar_hex_e_rgb():
    pal = paleta.carregar("acid")
    assert aplicar.renderizar("a {{accent}} b [{{rgb:foco}}]", pal) == "a #B8FF2E b [123, 77, 255]"


def test_renderizar_chave_desconhecida():
    with pytest.raises(KeyError):
        aplicar.renderizar("{{nao_existe}}", paleta.carregar("acid"))


def test_todo_template_renderiza_nas_duas_paletas():
    for nome in ("acid", "nightcity"):
        pal = paleta.carregar(nome)
        for tpl in (RAIZ / "templates").glob("*.tpl"):
            assert "{{" not in aplicar.renderizar(tpl.read_text(), pal), tpl.name


def _conteudo_seco(nome_paleta, tmp_path):
    aplicar.main(["--seco", "--paleta", nome_paleta, "--destino-seco", str(tmp_path)])
    arquivos = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert arquivos
    return {p: p.read_text(errors="ignore").upper() for p in arquivos}


def test_seco_acid_sem_cores_nightcity(tmp_path):
    for p, txt in _conteudo_seco("acid", tmp_path).items():
        for cor in NIGHTCITY:
            assert cor not in txt, f"{cor} em {p}"


def test_seco_nightcity_sem_cores_acid(tmp_path):
    for p, txt in _conteudo_seco("nightcity", tmp_path).items():
        for cor in ACID:
            assert cor not in txt, f"{cor} em {p}"


def test_esquema_do_terminal_tem_nome_do_tema(tmp_path):
    _conteudo_seco("acid", tmp_path)
    ron = next(tmp_path.rglob("color_schemes_dark")).read_text()
    assert re.search(r'name: "cyberdeck"', ron)


PERMITIDOS = ["cosmic-cyberdeck", "90-cosmic-cyberdeck"]  # caminhos/nomes de arquivo, não aparecem na tela


def test_configs_geradas_sem_texto_proibido(tmp_path):
    from poster import modulos
    aplicar.main(["--seco", "--paleta", "acid", "--destino-seco", str(tmp_path)])
    textos = [p.read_text(errors="ignore") for p in tmp_path.rglob("*") if p.is_file()]
    textos.append((RAIZ / "templates/fish-papel.fish").read_text())
    for t in textos:
        for perm in PERMITIDOS:
            t = t.replace(perm, "")
        assert not any(x in t.lower() for x in modulos.TEXTOS_PROIBIDOS)


def test_cava_dorme_em_silencio(tmp_path):
    aplicar.main(["--seco", "--paleta", "acid", "--destino-seco", str(tmp_path)])
    assert "sleep_timer = 3" in next(tmp_path.rglob("cava/config")).read_text()


def test_fish_aberto_recarrega_cores_ao_trocar_paleta(tmp_path):
    aplicar.main(["--seco", "--paleta", "acid", "--destino-seco", str(tmp_path)])
    cores = next(tmp_path.rglob("90-cyberdeck-cores.fish"))
    nc = paleta.carregar("nightcity")["accent"].lstrip("#")
    script = (f"source {cores}; echo antes $fish_color_command; "
              f"sed -i 's/B8FF2E/{nc}/' {cores}; set -g cyberdeck_paleta troca; echo depois $fish_color_command")
    import subprocess
    r = subprocess.run(["fish", "--no-config", "-i", "-c", script], capture_output=True, text=True)
    assert "antes B8FF2E" in r.stdout and f"depois {nc}" in r.stdout


def test_aplicar_avisa_apps_abertos(monkeypatch):
    chamados = []
    monkeypatch.setattr(aplicar, "_rodar", lambda *c: chamados.append([str(x) for x in c]))
    aplicar.avisar_abertos("acid")
    assert any(c[:2] == ["fish", "-c"] and "set -U cyberdeck_paleta acid" in c[2] for c in chamados)
    assert ["pkill", "-USR2", "-x", "cava"] in chamados


def test_paleta_do_tema_sem_envelope_do_builder():
    # o Builder guarda Dark((...)); o tema espera só a struct (...), senão o COSMIC ignora a paleta
    assert aplicar.paleta_do_tema('Dark((\n    name: "acid",\n))\n') == '(\n    name: "acid",\n)\n'
    assert aplicar.paleta_do_tema('(\n    name: "acid",\n)\n') == '(\n    name: "acid",\n)\n'


def test_cava_espelhado_fino_na_cor_do_tema(tmp_path):
    # cava 0.7.4 só aceita cor hex se o terminal redefinir a paleta (initc); o cosmic-term ignora e mostra
    # azul/verde puros (e sem essa capacidade o cava sai com erro). Cor por nome = cor do tema do terminal.
    aplicar.main(["--seco", "--paleta", "acid", "--destino-seco", str(tmp_path)])
    t = next(tmp_path.rglob("cava/config")).read_text()
    assert "channels = stereo" in t and "bar_width = 1" in t and "bar_spacing = 1" in t
    assert "gradient = 0" in t and "foreground = 'magenta'" in t and "'#" not in t


def test_pasta_criada_pelo_tema_nao_impede_de_escrever(tmp_path, monkeypatch):
    # depois de restaurar um backup some ~/.config/btop/themes etc.; reaplicar tem que recriar, não pular
    monkeypatch.setattr(aplicar, "H", tmp_path)
    (tmp_path / ".config").mkdir()
    assert not aplicar._falta_o_app(tmp_path / ".config/btop/themes/cyberdeck.theme")
    assert not aplicar._falta_o_app(tmp_path / ".config/cava/config")
    assert aplicar._falta_o_app(tmp_path / ".config/spicetify/Themes/cyberdeck/color.ini")   # Spicetify não instalado
