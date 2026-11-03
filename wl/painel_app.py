"""Janela do painel de arte vivo (slot de arte do ultrawide). Uso: python3 painel_app.py [TITULO]"""
import sys
import threading
import time
from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
gi.require_version("GdkWayland", "4.0")
from gi.repository import Gdk, GdkWayland, GLib, Gtk  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import paleta  # noqa: E402
import painel_dados  # noqa: E402
from poster import painel  # noqa: E402

TITULO = sys.argv[1] if len(sys.argv) > 1 else "cyberdeck:arte"
PAL = paleta.carregar()
estado = {"dados": {}, "tick": 0, "fixo": None, "tam": None}


def coletor():
    while True:
        estado["dados"] = painel_dados.coletar()
        time.sleep(5)


def main():
    GLib.set_prgname("cyberdeck.painel")
    Gtk.init()
    loop = GLib.MainLoop()
    w = Gtk.Window(title=TITULO)
    w.set_decorated(False)
    w.set_default_size(600, 968)
    pic = Gtk.Picture()
    pic.set_content_fit(Gtk.ContentFit.FILL)
    w.set_child(pic)
    w.connect("close-request", lambda *_: (loop.quit(), False)[1])

    def quadro():
        tam = (w.get_width() or 600, w.get_height() or 968)
        if estado["tam"] != tam:  # arte fixa só é redesenhada se a janela mudar de tamanho
            estado["fixo"], estado["tam"] = painel.base(PAL, tam), tam
        dados = {**estado["dados"], "hora": time.strftime("%H:%M")}
        chave = (tam, tuple(sorted((k, str(v)) for k, v in dados.items())))
        if chave == estado.get("ultimo"):
            return True  # nada mudou: não redesenha (economia de CPU)
        estado["ultimo"] = chave
        img = painel.render(dados, PAL, tam, estado["tick"], estado["fixo"])
        estado["tick"] += 1
        tex = Gdk.MemoryTexture.new(img.width, img.height, Gdk.MemoryFormat.R8G8B8,
                                    GLib.Bytes.new(img.tobytes()), img.width * 3)
        pic.set_paintable(tex)
        return True

    w.present()
    sup = w.get_surface()
    if isinstance(sup, GdkWayland.WaylandToplevel):
        sup.set_application_id("cyberdeck.painel")
    threading.Thread(target=coletor, daemon=True).start()
    quadro()
    GLib.timeout_add_seconds(2, quadro)
    loop.run()


if __name__ == "__main__":
    main()
