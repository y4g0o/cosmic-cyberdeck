"""install.py: backup antes de mexer, desfazer restaura exatamente o que havia. Tudo num HOME temporário."""
import json

import pytest

import aplicar
import install
import paleta


@pytest.fixture
def casa(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    # os destinos vêm do HOME do processo (aplicar.H); as operações de arquivo usam só `casa`
    return tmp_path


def test_alvos_cobrem_templates_e_pastas_do_cosmic(casa):
    lista = dict(install.alvos(casa, paleta.carregar("acid")))
    assert lista[".config/starship.toml"] == "file"
    assert lista[".config/cosmic/com.system76.CosmicTheme.Dark/v1"] == "dir"
    assert ".config/fish/conf.d/91-cyberdeck-comando.fish" in lista
    assert not any(p.startswith("/") or ".." in p for p in lista)          # tudo dentro do HOME
    assert install.AUTOSTART not in lista
    assert install.AUTOSTART in dict(install.alvos(casa, paleta.carregar("acid"), autostart=True))


def test_backup_e_restauracao_voltam_ao_estado_anterior(casa):
    (casa / ".config").mkdir()
    (casa / ".config/starship.toml").write_text("original\n")
    tema = casa / ".config/cosmic/com.system76.CosmicTheme.Dark/v1"
    tema.mkdir(parents=True)
    (tema / "accent").write_text("rosa")
    lista = [(".config/starship.toml", "file"), (".config/cosmic/com.system76.CosmicTheme.Dark/v1", "dir"),
             (".config/cava/config", "file")]
    pasta = install.fazer_backup(casa, lista, "acid")
    assert pasta.parent == casa / ".local/share/cosmic-cyberdeck/backups"
    # "instalação": muda, cria e gera
    (casa / ".config/starship.toml").write_text("tema\n")
    (tema / "accent").write_text("verde")
    (tema / "chave_nova").write_text("x")
    (casa / ".config/cava").mkdir()
    (casa / ".config/cava/config").write_text("novo")
    (casa / ".local/share/icons/Papirus-cyberdeck").mkdir(parents=True)

    feito = install.restaurar(casa, pasta)
    assert (casa / ".config/starship.toml").read_text() == "original\n"
    assert (tema / "accent").read_text() == "rosa" and not (tema / "chave_nova").exists()
    assert not (casa / ".config/cava/config").exists()                       # não existia: some
    assert not (casa / ".local/share/icons/Papirus-cyberdeck").exists()      # gerado por nós: some
    assert any("restaurado" in f for f in feito)
    assert json.loads((pasta / "manifest.json").read_text())["restored"]


def test_desinstalar_pega_o_mais_recente_ainda_nao_restaurado(casa):
    a = install.fazer_backup(casa, [], "acid", agora=1_700_000_000)
    b = install.fazer_backup(casa, [], "acid", agora=1_700_000_100)
    assert install.ultimo_nao_restaurado(casa) == b
    install.restaurar(casa, b)
    assert install.ultimo_nao_restaurado(casa) == a
    install.restaurar(casa, a)
    assert install.ultimo_nao_restaurado(casa) is None
    assert install.main(["--uninstall"], home=casa) == 1                     # nada mais a restaurar


def test_dry_run_nao_toca_no_home(casa, capsys):
    (casa / ".config").mkdir()
    (casa / ".config/starship.toml").write_text("meu prompt\n")
    antes = sorted(p.relative_to(casa) for p in casa.rglob("*"))
    assert install.main(["--dry-run", "--paleta", "acid"], home=casa) == 0
    assert sorted(p.relative_to(casa) for p in casa.rglob("*")) == antes
    assert (casa / ".config/starship.toml").read_text() == "meu prompt\n"
    out = capsys.readouterr().out
    assert "backup + sobrescrever" in out and "~/.config/starship.toml" in out


def test_instalar_recusa_sem_cosmic(casa, monkeypatch):
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "GNOME")
    assert install.main(["--yes"], home=casa) == 1
    assert not (casa / ".local/share/cosmic-cyberdeck/backups").exists()


def test_tema_original_guardado_so_uma_vez_e_nunca_um_tema_nosso(casa):
    tema = casa / ".config/cosmic/com.system76.CosmicTheme.Dark/v1"
    tema.mkdir(parents=True)
    (tema / "name").write_text('"acid"')                                      # já é tema do cyberdeck
    install.guardar_tema_original(casa)
    assert not (casa / ".local/share/cosmic-cyberdeck/original").exists()
    (tema / "name").write_text('"cosmic-dark"')
    install.guardar_tema_original(casa)
    guardado = casa / ".local/share/cosmic-cyberdeck/original/CosmicTheme.Dark.v1/name"
    assert guardado.read_text() == '"cosmic-dark"'
    (tema / "name").write_text('"outro"')
    install.guardar_tema_original(casa)
    assert guardado.read_text() == '"cosmic-dark"'


def test_templates_sem_caminho_fixo_de_usuario():
    for tpl in (install.RAIZ / "templates").iterdir():
        txt = tpl.read_text()
        assert "/".join(["", "home", ""]) not in txt and "~/cosmic-cyberdeck" not in txt, tpl.name   # nenhum caminho fixo de usuário
    desk = aplicar.renderizar((install.RAIZ / "templates/autostart-cyberdeck.desktop").read_text(), paleta.carregar("acid"))
    assert str(install.RAIZ / "ao_entrar.sh") in desk
