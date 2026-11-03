"""Janela-fantasma: ocupa um slot do tiling e é 100% transparente, deixando o pôster aparecer.

Uso: python3 fantasma.py NOME   (título "cyberdeck:NOME"). Sem Gtk.Application para não depender do D-Bus.
"""
import sys

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
gi.require_version("GdkWayland", "4.0")
from gi.repository import Gdk, GdkWayland, GLib, Gtk  # noqa: E402

CSS = b"window, window.background { background: rgba(0, 0, 0, 0.01); box-shadow: none; border: none; }"


def main():
    nome = sys.argv[1] if len(sys.argv) > 1 else "arte"
    GLib.set_prgname("cyberdeck.fantasma")  # vira o app_id no Wayland
    Gtk.init()
    prov = Gtk.CssProvider()
    prov.load_from_data(CSS)
    Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), prov, Gtk.STYLE_PROVIDER_PRIORITY_USER)
    loop = GLib.MainLoop()
    w = Gtk.Window(title=f"cyberdeck:{nome}")
    w.set_decorated(False)
    w.set_default_size(200, 200)
    w.connect("close-request", lambda *_: (loop.quit(), False)[1])
    w.present()
    sup = w.get_surface()
    if isinstance(sup, GdkWayland.WaylandToplevel):
        sup.set_application_id("cyberdeck.fantasma")
    print("fantasma: janela apresentada", flush=True)
    loop.run()


if __name__ == "__main__":
    main()
