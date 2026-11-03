import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))


def pytest_configure(config):
    config.addinivalue_line("markers", "wayland: needs a live COSMIC Wayland session (skipped otherwise)")


_PRECISAM_DE_FONTES = {"test_compor.py", "test_modulos.py", "test_painel.py", "test_boot.py", "test_placas.py"}


def pytest_collection_modifyitems(config, items):
    """Sem as fontes (ex.: Noto Sans CJK fora do Pop!_OS) os testes que desenham texto são pulados, com aviso."""
    import pytest
    from poster import modulos
    faltam = modulos.fontes_faltando()
    if not faltam:
        return
    pular = pytest.mark.skip(reason=f"missing fonts: {', '.join(faltam)} (see README > Requirements; "
                                    "Noto Sans CJK: `sudo apt install fonts-noto-cjk`)")
    for item in items:
        if item.path.name in _PRECISAM_DE_FONTES:
            item.add_marker(pular)
