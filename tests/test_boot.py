from pathlib import Path

import pytest
from PIL import Image

import gerar_boot as gb
import paleta
from poster import modulos


@pytest.mark.skipif(not Path("/usr/share/plymouth/themes/pop-basic").is_dir(),
                    reason="precisa do tema pop-basic do Plymouth (Pop!_OS)")
def test_tema_do_boot_usa_a_paleta_e_mantem_a_senha(tmp_path):
    pal = paleta.carregar("acid")
    tema = gb.gerar(tmp_path, pal)
    cfg = (tema / "cyberdeck.plymouth").read_text()
    assert "ModuleName=two-step" in cfg   # mesmo módulo do Pop: diálogo de senha continua funcionando
    assert "BackgroundStartColor=0x060609" in cfg and "ProgressBarForegroundColor=0xb8ff2e" in cfg
    assert f"ImageDir=/usr/share/plymouth/themes/cyberdeck" in cfg
    assert not any(p in cfg.lower() for p in modulos.TEXTOS_PROIBIDOS)
    for nome in ("entry.png", "lock.png", "bullet.png"):
        assert (tema / nome).exists()
    marca = Image.open(tema / "header-image.png")
    assert marca.size == (200, 250) and marca.mode == "RGBA"
    assert Image.open(tema / "bgrt-fallback.png").size == (200, 250)
    assert any("POP!_OS" in l and "COSMIC" in l for l in gb.LEGENDA)


def test_script_de_instalacao_e_reversivel(tmp_path):
    sh = gb.script_instalar()
    assert "update-alternatives --install" in sh and "update-initramfs -u" in sh
    assert "update-alternatives --set default.plymouth /usr/share/plymouth/themes/pop-basic/pop-basic.plymouth" in sh
