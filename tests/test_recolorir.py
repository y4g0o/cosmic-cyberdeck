import recolorir_tema as rt


def test_chave_nova_do_cosmic_entra_no_tema(tmp_path):
    # COSMIC 1.11 trouxe list_button; sem ela o tema inteiro dá erro ao carregar
    d, origem, sistema = (tmp_path / n for n in ("d", "origem", "sistema"))
    for p in (d, origem, sistema):
        p.mkdir()
    (d / "accent").write_text("d")
    (origem / "accent").write_text("origem")
    (sistema / "accent").write_text("sistema")
    (sistema / "list_button").write_text("sistema")
    fontes = rt.fontes_do_tema(d, origem, sistema)
    assert {n: p.read_text() for n, p in fontes.items()} == {"accent": "origem", "list_button": "sistema"}
