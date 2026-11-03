import verificar_tema as vt


def test_tema_saudavel_nao_tem_problema(tmp_path):
    usr, sis = tmp_path / "usr", tmp_path / "sis"
    for d in (usr, sis):
        d.mkdir()
        (d / "accent").write_text("(1.0)")
    (usr / "palette").write_text('(\n    name: "acid",\n)\n')
    (sis / "palette").write_text('(\n    name: "cosmic-dark",\n)\n')
    assert vt.problemas(usr, sis) == []


def test_acusa_chave_nova_do_cosmic_e_paleta_no_formato_do_builder(tmp_path):
    usr, sis = tmp_path / "usr", tmp_path / "sis"
    usr.mkdir(); sis.mkdir()
    (usr / "palette").write_text('Dark((\n    name: "acid",\n))\n')
    (sis / "palette").write_text("(\n)\n")
    (sis / "list_button").write_text("(\n)\n")   # chave que uma atualização do COSMIC trouxe
    assert vt.problemas(usr, sis) == ["chave nova do COSMIC: list_button", "paleta no formato do Builder"]


def test_consertar_com_sucesso_sai_com_0(monkeypatch, tmp_path):
    monkeypatch.setattr(vt, "problemas", lambda u, s: ["chave nova do COSMIC: x"])
    monkeypatch.setattr(vt, "consertar", lambda: None)
    assert vt.main(["--consertar"]) == 0
    assert vt.main([]) == 1          # só verificar, com problema: 1
