"""Cliente Wayland mínimo para o COSMIC: lê monitores, áreas de trabalho e janelas, e executa as ações do cyberdeck.

Protocolos: ext-workspace-v1, cosmic-workspace-unstable-v2 (tiling), ext-foreign-toplevel-list-v1,
cosmic-toplevel-info-unstable-v1 (saída/área/geometria) e cosmic-toplevel-management-unstable-v1 (mover/ativar).
"""
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from pywayland.client import Display  # noqa: E402

from protocol.cosmic_toplevel_info_unstable_v1 import ZcosmicToplevelInfoV1  # noqa: E402
from protocol.cosmic_toplevel_management_unstable_v1 import ZcosmicToplevelManagerV1  # noqa: E402
from protocol.cosmic_workspace_unstable_v2 import ZcosmicWorkspaceManagerV2  # noqa: E402
from protocol.ext_foreign_toplevel_list_v1 import ExtForeignToplevelListV1  # noqa: E402
from protocol.ext_workspace_v1 import ExtWorkspaceManagerV1  # noqa: E402
from protocol.wayland import WlOutput, WlSeat  # noqa: E402

TILING_ON, TILING_OFF = 1, 0


class Cosmic:
    def __init__(self):
        self.d = Display()
        self.d.connect()
        self.saidas = {}      # WlOutput proxy -> nome
        self.grupos = {}      # group proxy -> {"saidas": set(nomes)}
        self.areas = {}       # ws proxy -> {nome, coord, estado, grupo, tiling, cosmic}
        self.janelas = {}     # foreign proxy -> {app_id, titulo, saidas, areas, geom, cosmic}
        self._g = {}
        self._mortas = []
        # registros guardados no objeto: o pywayland acha o display pelos WlRegistry vivos e, sem eles,
        # descarta toda janela nova ("Cannot find display") quando a coleta de lixo passa
        reg = self._reg = self.d.get_registry()
        reg.dispatcher["global"] = lambda r, n, i, v: (self._g.setdefault(i, (n, v)), None)[1]
        self.d.roundtrip()

        def bind(iface, cls, versao):
            nome, v = self._g[iface]
            return reg.bind(nome, cls, min(v, versao))

        self._saidas_registro(reg)
        self.seat = bind("wl_seat", WlSeat, 1)
        self.ws = bind("ext_workspace_manager_v1", ExtWorkspaceManagerV1, 1)
        self.cws = bind("zcosmic_workspace_manager_v2", ZcosmicWorkspaceManagerV2, 2)
        self.lista = bind("ext_foreign_toplevel_list_v1", ExtForeignToplevelListV1, 1)
        self.info = bind("zcosmic_toplevel_info_v1", ZcosmicToplevelInfoV1, 3)
        self.gerente = bind("zcosmic_toplevel_manager_v1", ZcosmicToplevelManagerV1, 4)
        self.ws.dispatcher["workspace_group"] = self._novo_grupo
        self.ws.dispatcher["workspace"] = self._nova_area
        self.lista.dispatcher["toplevel"] = self._nova_janela
        for _ in range(2):
            self.d.roundtrip()
        self.atualizar()

    # ---------- registro ----------
    def _saidas_registro(self, reg):
        globais = []
        reg2 = self._reg_saidas = self.d.get_registry()
        reg2.dispatcher["global"] = lambda r, n, i, v: globais.append((n, i, v))
        self.d.roundtrip()
        for n, i, v in globais:
            if i == "wl_output":
                o = reg2.bind(n, WlOutput, min(v, 4))
                o.dispatcher["name"] = lambda p, nome: self.saidas.__setitem__(p, nome)
        self.d.roundtrip()

    def _novo_grupo(self, _m, g):
        self.grupos[g] = {"saidas": set()}
        g.dispatcher["output_enter"] = lambda p, o: self.grupos[p]["saidas"].add(self.saidas.get(o))
        g.dispatcher["workspace_enter"] = lambda p, w: self.areas.setdefault(w, {}).__setitem__("grupo", p)

    def _nova_area(self, _m, w):
        a = self.areas.setdefault(w, {})
        a.update(nome=None, coord=(), estado=0, tiling=None)
        w.dispatcher["name"] = lambda p, n: self.areas[p].__setitem__("nome", n)
        w.dispatcher["coordinates"] = lambda p, c: self.areas[p].__setitem__("coord", tuple(c))
        w.dispatcher["state"] = lambda p, s: self.areas[p].__setitem__("estado", s)
        c = self.cws.get_cosmic_workspace(w)
        c.dispatcher["tiling_state"] = lambda p, t, w=w: self.areas[w].__setitem__("tiling", t)
        a["cosmic"] = c

    def _nova_janela(self, _l, h):
        j = self.janelas[h] = {"app_id": "", "titulo": "", "saidas": set(), "areas": set(), "geom": None}
        h.dispatcher["app_id"] = lambda p, x: self.janelas[p].__setitem__("app_id", x)
        h.dispatcher["title"] = lambda p, x: self.janelas[p].__setitem__("titulo", x)
        h.dispatcher["closed"] = lambda p: self._fechou(p)
        c = self.info.get_cosmic_toplevel(h)
        c.dispatcher["output_enter"] = lambda p, o, h=h: self.janelas.get(h, {}).get("saidas", set()).add(self.saidas.get(o))
        c.dispatcher["ext_workspace_enter"] = lambda p, w, h=h: self.janelas.get(h, {}).get("areas", set()).add(w)
        c.dispatcher["ext_workspace_leave"] = lambda p, w, h=h: self.janelas.get(h, {}).get("areas", set()).discard(w)
        c.dispatcher["geometry"] = lambda p, o, x, y, wd, ht, h=h: self.janelas.get(h, {}).__setitem__("geom", (self.saidas.get(o), x, y, wd, ht))
        j["cosmic"] = c

    def _fechou(self, h):
        # guarda os proxies: liberá-los com eventos ainda em trânsito derruba o cffi (segfault)
        self._mortas.append(self.janelas.pop(h, None))

    # ---------- consultas ----------
    def saida_de(self, area):
        g = self.areas[area].get("grupo")
        return next(iter(self.grupos.get(g, {}).get("saidas", {None})))

    def areas_da_saida(self, saida):
        ws = [w for w in self.areas if self.saida_de(w) == saida]
        return sorted(ws, key=lambda w: self.areas[w].get("coord") or (0,))

    def wl_output(self, nome):
        return next(p for p, n in self.saidas.items() if n == nome)

    # ---------- ações ----------
    def ativar_area(self, area):
        area.activate()
        self.ws.commit()
        self.d.roundtrip()

    def tiling(self, area, ligado: bool):
        self.areas[area]["cosmic"].set_tiling_state(TILING_ON if ligado else TILING_OFF)
        self.ws.commit()
        self.d.roundtrip()

    def mover(self, janela, area, saida):
        self.gerente.move_to_ext_workspace(self.janelas[janela]["cosmic"], area, self.wl_output(saida))
        self.d.roundtrip()

    def ativar_janela(self, janela):
        self.gerente.activate(self.janelas[janela]["cosmic"], self.seat)
        self.d.roundtrip()

    def atualizar(self, ciclos=3, espera=0.05):
        # o COSMIC só envia dados de janela no próximo ciclo dele: espera curta + roundtrip
        for _ in range(ciclos):
            time.sleep(espera)
            self.d.roundtrip()


if __name__ == "__main__":
    import os
    c = Cosmic()
    for nome in sorted(set(c.saidas.values())):
        print(f"== {nome}")
        for i, w in enumerate(c.areas_da_saida(nome), 1):
            a = c.areas[w]
            print(f"  área {i}: nome={a.get('nome')!r} coord={a.get('coord')} ativa={bool(a.get('estado', 0) & 1)} tiling={a.get('tiling')}")
    print("== janelas")
    for j in c.janelas.values():
        areas = [c.areas_da_saida(c.saida_de(w)).index(w) + 1 for w in j["areas"] if w in c.areas]
        print(f"  {j['app_id']:<32} {j['titulo'][:30]:<30} saida={sorted(s for s in j['saidas'] if s)} area={areas} geom={j['geom']}")
    sys.stdout.flush()
    os._exit(0)  # evita crash do cffi ao destruir proxies na saída
