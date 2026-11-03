"""Comando `cyberdeck`: monta a base de janelas nos slots do layout.toml (tiling na área vazia final de cada monitor).

Uso: cyberdeck [--plano]      (--plano só mostra o que faria)
Nunca fecha janelas. Apps já abertos são movidos; os que faltam são abertos.
"""
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import layout

RAIZ = Path(__file__).resolve().parent
FISH = shutil.which("fish") or "/usr/bin/fish"


def _term(papel):
    return {"cmd": ["cosmic-term"], "env": {"SHELL": FISH, "CYBERDECK_PAPEL": papel},
            "casa": lambda j, p=papel: j["titulo"].startswith(f"cyberdeck:{p}")}


APPS = {
    "spotify": {"cmd": ["spotify", "--enable-features=UseOzonePlatform,WaylandWindowDecorations", "--ozone-platform=wayland"],
                "casa": lambda j: j["app_id"].lower() == "spotify"},
    "terminal_livre": _term("livre"),
    "cava": {**_term("cava"), "casa": lambda j: j["titulo"].startswith("cyberdeck:cava") or j["titulo"].split(" — ")[0] == "cava"},
    "hud": _term("hud"),
    "arte": {"cmd": ["/usr/bin/python3", str(RAIZ / "wl/painel_app.py"), "cyberdeck:arte"], "casa": lambda j: j["titulo"] == "cyberdeck:arte"},
    "brave": {"cmd": ["brave-browser", "--profile-directory=Default"],   # perfil padrão, sem a tela de escolha
              "casa": lambda j: j["app_id"] == "brave-browser"},
    "arquivos": {"cmd": ["cosmic-files"], "casa": lambda j: j["app_id"] == "com.system76.CosmicFiles"},
}


_PAPEIS = ("cyberdeck:", "cava")  # terminais com papel fixo (hud, cava...) nunca contam como terminal livre


def e_do_slot(slot: str, j: dict, na_area: bool) -> bool:
    """A janela pertence ao slot? O terminal livre troca de título (ex.: um editor aberto nele): dentro da área do cyberdeck,
    qualquer terminal sem papel conta como ele; fora dela só o de título cyberdeck:livre (não rouba outros terminais)."""
    if APPS[slot]["casa"](j):
        return True
    return (slot == "terminal_livre" and na_area and j["app_id"] == "com.system76.CosmicTerm"
            and not j["titulo"].startswith(_PAPEIS))


@dataclass(frozen=True)
class Acao:
    tipo: str          # abrir | mover | retirar
    slot: str
    saida: str
    foco: str | None   # slot que deve estar focado antes de inserir (o que será dividido)


def _primeira(no):
    return no if isinstance(no, str) else _primeira(no[1][0])


def ordem_insercao(arvore) -> list[tuple[str, str | None]]:
    """Ordem para o tiling do COSMIC reproduzir a árvore: foca a 1ª folha de 'a' e insere a 1ª folha de 'b'."""
    def andar(no):
        if isinstance(no, str):
            return []
        a, b = no[1]
        return [(_primeira(b), _primeira(a))] + andar(a) + andar(b)
    return [(_primeira(arvore), None)] + andar(arvore)


def _folhas(no) -> list[str]:
    return [no] if isinstance(no, str) else _folhas(no[1][0]) + _folhas(no[1][1])


def giros(L, saida) -> set[str]:
    """Slots cuja inserção cria uma divisão contra o lado mais longo (o COSMIC faria a outra): depois de
    inseri-los, o cyberdeck gira a divisão com Super+O. Mesma ordem (pré-ordem) de ordem_insercao e divisoes."""
    nos = []

    def andar(no):
        if not isinstance(no, str):
            nos.append(no)
            andar(no[1][0])
            andar(no[1][1])
    andar(L.arvore(saida))
    return {_primeira(no[1][1]) for no, (direcao, r) in zip(nos, L.divisoes(saida))
            if (direcao == "H") != (r.w >= r.h)}


ESPERAS_GIRO = (0, 0.5, 1, 1.5, 2, 2)   # entre tentativas (cada uma com teclado virtual novo); com tudo bem basta a 1ª


def direcao_do_giro(arvore, slot):
    """Direção ('H'/'V') da divisão que a inserção de `slot` cria, ou None se ele não divide nada."""
    if isinstance(arvore, str):
        return None
    direcao, (a, b) = arvore
    if _primeira(b) == slot:
        return direcao
    return direcao_do_giro(a, slot) or direcao_do_giro(b, slot)


def girou_certo(direcao, foco, novo) -> bool:
    """A janela nova ficou do lado que a árvore pede em relação à que ela dividiu? (V: embaixo; H: à direita)"""
    if direcao == "V":
        return novo.y >= foco.y + foco.h and novo.x < foco.x + foco.w and foco.x < novo.x + novo.w
    return novo.x >= foco.x + foco.w and novo.y < foco.y + foco.h and foco.y < novo.y + novo.h


def _parado(c, hs, segundos=2.0, de=None):
    """Espera as janelas pararem de mudar (animação do tiling) e devolve os retângulos delas. Com `de` (os
    retângulos antes do atalho), primeiro espera eles mudarem: logo após a tecla nada mudou ainda, e julgar
    nessa hora faz tentar de novo e desfazer o giro que estava a caminho."""
    fim, antes = time.time() + segundos, None
    while de is not None and time.time() < fim and _rects(c, hs) == de:
        c.atualizar(1, 0.15)
    while time.time() < fim:
        c.atualizar(1, 0.15)
        agora = _rects(c, hs)
        if agora == antes:
            break
        antes = agora
    return _rects(c, hs)


def proximo_ajuste(arvore, atuais: dict, alvo: dict, tolerancia: int = 6) -> tuple[str, str] | None:
    """Próximo passo para as divisórias baterem com `alvo` (tamanhos gravados): (slot a focar, seta do
    Super+R, que faz a janela crescer para aquele lado). De cima para baixo na árvore; None = já bate."""
    if isinstance(arvore, str):
        return None
    direcao, (a, b) = arvore
    fa, fb = _folhas(a), _folhas(b)
    fim = (lambda r: r.x + r.w) if direcao == "H" else (lambda r: r.y + r.h)
    ini = (lambda r: r.x) if direcao == "H" else (lambda r: r.y)
    d = max(fim(alvo[n]) for n in fa) - max(fim(atuais[n]) for n in fa)
    if d > tolerancia:     # a precisa crescer: a folha de a encostada na divisória cresce para o lado de b
        return max(fa, key=lambda n: fim(atuais[n])), "right" if direcao == "H" else "down"
    if d < -tolerancia:    # b precisa crescer: a folha de b encostada na divisória cresce para o lado de a
        return min(fb, key=lambda n: ini(atuais[n])), "left" if direcao == "H" else "up"
    return proximo_ajuste(a, atuais, alvo, tolerancia) or proximo_ajuste(b, atuais, alvo, tolerancia)


def sobra_pequena(arvore, atuais: dict, alvo: dict) -> bool:
    """Diferença que o ajuste fino não tira (passo de 12 px) e o pôster pode absorver: dentro da tolerância,
    mas não exata. Montagem errada nunca conta, para não gravar por cima dos tamanhos escolhidos."""
    return proximo_ajuste(arvore, atuais, alvo) is None and atuais != alvo


def plano_abertura(L, existentes: set[str], no_lugar: set[str], saidas: list[str],
                   intrusos: set[str] = frozenset()) -> list[Acao]:
    """existentes: slots com janela aberta; no_lugar: slots já na área do cyberdeck;
    intrusos: saídas cuja área do cyberdeck tem janelas de fora (elas são retiradas e o layout é refeito)."""
    acoes = []
    for s in [x for x in L.saidas() if x in saidas]:
        ordem = ordem_insercao(L.arvore(s))
        slots = [n for n, _ in ordem]
        if all(n in no_lugar for n in slots) and s not in intrusos:
            continue
        acoes += [Acao("retirar", n, s, None) for n in slots if n in no_lugar]  # remonta do zero, na ordem certa
        for n, foco in ordem:
            acoes.append(Acao("mover" if n in existentes else "abrir", n, s, foco))
    return acoes


def desalinhada(L, saida: str, geometrias: dict) -> bool:
    """True se alguma janela de slot está fora do retângulo do layout (ex.: layout.toml mudou).
    Com tamanhos gravados à mão (`--gravar`) basta o centro da janela cair no retângulo dela: diferença
    de poucos pixels o ajuste fino (Super+R) resolve; lado trocado exige remontar."""
    esperado = {**L.slots(saida), **L.zonas(saida)}
    medido = L.tem_medido(saida)
    for slot, g in geometrias.items():
        r = esperado.get(slot)
        if not (r and g):
            continue
        if medido:
            cx, cy = g[0] + g[2] / 2, g[1] + g[3] / 2
            if not (r.x <= cx < r.x + r.w and r.y <= cy < r.y + r.h):
                return True
        elif tuple(g) != (r.x, r.y, r.w, r.h):
            return True
    return False


# ---------- execução (Wayland) ----------
def _cosmic():
    sys.path.insert(0, str(RAIZ / "wl"))
    from cosmic import Cosmic
    return Cosmic()


def _esperar(c, pred, antes, segundos=20):
    """Janela nova que satisfaz `pred`, só quando já está na tela e parada (mesma geometria em dois ciclos):
    anunciada mas ainda sem posição, ela ignora o "mover" e nasce colada na janela em foco."""
    fim = time.time() + segundos
    ultima = {}
    while time.time() < fim:
        c.atualizar(1, 0.15)
        for h, j in c.janelas.items():
            if h in antes or not pred(j) or not j["geom"] or not j["areas"]:
                continue
            if ultima.get(h) == j["geom"]:
                return h
            ultima[h] = j["geom"]
    return None


def empurrao(pos: dict, saida: str) -> tuple[int, int]:
    """Movimento que leva o cursor para dentro de `saida`: para o lado de fora e, com monitores desnivelados,
    para a borda que só ele tem (senão o cursor trava na beira do outro monitor)."""
    x, y = pos[saida]
    dx = -300 if x == min(px for px, _ in pos.values()) else 300
    ys = {py for _, py in pos.values()}
    dy = 0 if len(ys) == 1 else (300 if y == max(ys) else -300)
    return dx, dy


class _Entrada:
    """Teclado e mouse virtuais, criados só quando algum atalho for preciso."""
    def __init__(self):
        sys.path.insert(0, str(RAIZ / "wl"))
        from teclado import Mouse, Teclado
        self.teclado, self.mouse, self.pos = Teclado(), Mouse(), layout.posicoes()

    def preparar(self, c, h, saida):
        """Foca a janela e leva o cursor ao monitor dela (o COSMIC aplica os atalhos onde está o cursor)."""
        c.ativar_janela(h)
        c.atualizar(3)
        if saida in self.pos:
            self.mouse.empurrar(*empurrao(self.pos, saida))

    def fechar(self):
        self.teclado.fechar()
        self.mouse.fechar()


def _janelas_dos_slots(c, L, saida, area) -> dict:
    hs = {}
    for slot in L.slots(saida):
        for h, j in c.janelas.items():
            if area in j["areas"] and e_do_slot(slot, j, True) and j["geom"]:
                hs[slot] = h
                break
    return hs


def _rects(c, hs: dict) -> dict:
    """Retângulo de cada slot; janela que fechou no meio (ou ainda sem geometria) fica de fora."""
    return {n: layout.Rect(*c.janelas[h]["geom"][1:]) for n, h in hs.items()
            if h in c.janelas and c.janelas[h]["geom"]}


def ajustar(c, L, saidas, ent=None):
    """Empurra as divisórias (Super+R + setas) até as janelas baterem com os tamanhos gravados.
    Devolve (entrada usada ou None, monitores com sobra pequena que só o pôster pode absorver)."""
    sobra = set()
    for s in saidas:
        if not L.tem_medido(s):
            continue
        area, alvo = _area_do_layout(c, s, L), L.slots(s)
        recriado = False

        def passo_de(r):   # janela fechou no meio: não há passo (e o laço para)
            return proximo_ajuste(L.arvore(s), r, alvo) if set(r) == set(alvo) else "fechou"
        for _ in range(30):
            hs = _janelas_dos_slots(c, L, s, area)
            if set(hs) != set(alvo) or set(_rects(c, hs)) != set(alvo):
                break
            passo = passo_de(_rects(c, hs))
            if passo is None:
                break
            slot, seta = passo
            ent = ent or _Entrada()
            ent.preparar(c, hs[slot], s)
            antes = _rects(c, hs)
            with ent.teclado.segurando("super+r"):
                for _ in range(80):
                    ent.teclado.tocar(seta, pausa=0.05)
                    c.atualizar(2)
                    if passo_de(_rects(c, hs)) != passo:
                        break
            if _rects(c, hs) == antes:
                ent.fechar()   # teclado virtual ignorado: tenta uma vez com outro antes de desistir
                ent = None
                if recriado:
                    print(f"! {s}: o COSMIC não deixou ajustar {slot}")
                    break
                recriado = True
            else:
                recriado = False
        r = _rects(c, _janelas_dos_slots(c, L, s, area))
        if set(r) == set(alvo) and sobra_pequena(L.arvore(s), r, alvo):
            sobra.add(s)
        elif set(r) != set(alvo) or proximo_ajuste(L.arvore(s), r, alvo):
            print(f"! {s}: não montou certo; tamanhos gravados mantidos (rode o cyberdeck de novo)")
    return ent, sobra


def _area_do_layout(c, saida, L):
    """Área já usada pelo cyberdeck (tem janela de algum slot deste monitor), a do terminal em uso (se o monitor
    tem terminal livre) ou a área vazia final do monitor."""
    areas = c.areas_da_saida(saida)

    def janelas_do_layout(w):   # o terminal em uso conta como terminal livre
        return sum(w in j["areas"] and any(e_do_slot(n, j, True) for n in L.slots(saida)) for j in c.janelas.values())
    contagem = [janelas_do_layout(w) for w in areas]
    if max(contagem, default=0) == 0:
        return areas[-1]
    return areas[contagem.index(max(contagem))]   # a com mais janelas do layout (empate: a primeira)


def _fora(c, saida, alvo):
    """Área para onde retirar janelas: a vazia do final (se não for a do cyberdeck), senão a anterior a ela."""
    areas = c.areas_da_saida(saida)
    if areas[-1] != alvo:
        return areas[-1]
    i = areas.index(alvo)
    return areas[i - 1] if i > 0 else areas[0]


def _maior(c, handles):
    def area(h):
        g = c.janelas[h]["geom"]
        return g[3] * g[4] if g else 0
    return max(handles, key=area)


def intrusos_na_area(c, saida, area, L) -> list:
    """Janelas na área do cyberdeck que não pertencem a nenhum slot deste monitor."""
    slots = list(L.slots(saida)) + list(L.zonas(saida))
    return [h for h, j in c.janelas.items()
            if area in j["areas"] and not any(e_do_slot(n, j, True) for n in slots)]


def executar(c, L, acoes, saidas, ent=None):
    areas = {s: _area_do_layout(c, s, L) for s in saidas if s in L.saidas()}
    girar = {s: giros(L, s) for s in areas}
    for s, w in areas.items():
        for h in intrusos_na_area(c, s, w, L):
            c.mover(h, _fora(c, s, w), s)
        c.tiling(w, True)
    janela, falhas, retirados = {}, [], {}
    t0 = time.time()
    for a in acoes:
        try:
            alvo = areas[a.saida]
            spec = APPS[a.slot]
            if a.tipo == "retirar":
                hs = [h for h, j in c.janelas.items() if alvo in j["areas"] and e_do_slot(a.slot, j, True)]
                for h in hs:
                    c.mover(h, _fora(c, a.saida, alvo), a.saida)
                if hs:
                    retirados[a.slot] = hs[0]   # fora da área o terminal livre não é mais reconhecido pelo título
                continue
            if a.tipo == "abrir":
                antes = set(c.janelas)
                subprocess.Popen(spec["cmd"], env={**os.environ, **spec.get("env", {})},
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
                                 cwd=Path.home())
                h = _esperar(c, spec["casa"], antes)
                if h is None:
                    raise RuntimeError("janela não apareceu a tempo")
                # a janela nova nasce colada na que estiver em foco (às vezes o próprio terminal): estaciona
                # fora da área e entra como as movidas, ao lado do slot certo
                vaga = _fora(c, a.saida, alvo)
                print(f"        {a.slot}: estaciona na área {c.areas[vaga].get('nome')} (layout na {c.areas[alvo].get('nome')})")
                c.mover(h, vaga, a.saida)
                c.atualizar(2)
            if a.foco and a.foco in janela:
                c.ativar_janela(janela[a.foco])
                c.atualizar(2)
            if a.tipo == "mover":
                hs = [h for h, j in c.janelas.items() if e_do_slot(a.slot, j, alvo in j["areas"])]
                if retirados.get(a.slot) in c.janelas:
                    h = retirados[a.slot]
                elif hs:
                    h = _maior(c, hs)  # várias janelas (ex.: Brave): a maior
                else:
                    raise RuntimeError("janela sumiu antes de mover")
            c.mover(h, alvo, a.saida)
            c.atualizar(3)
            janela[a.slot] = h
            if a.slot in girar[a.saida]:   # divisão contra o lado mais longo: Super+O na janela recém-inserida
                direcao = direcao_do_giro(L.arvore(a.saida), a.slot)
                par = {a.foco: janela[a.foco], a.slot: h} if a.foco in janela else {a.slot: h}
                # confere e insiste: enquanto um app recém-aberto termina de carregar (o Spotify leva uns
                # segundos) ele toma o foco e o Super+O se perde; a cada volta refoca a janela e espera mais
                for espera in ESPERAS_GIRO:
                    time.sleep(espera)
                    ent = ent or _Entrada()
                    ent.preparar(c, h, a.saida)
                    de = _rects(c, par)
                    ent.teclado.atalho("super+o")
                    r = _parado(c, par, de=de)
                    print(f"        giro {a.slot}: {r}")
                    if a.foco not in r or a.slot not in r or girou_certo(direcao, r[a.foco], r[a.slot]):
                        break
                    if r != de:   # o atalho fez efeito e mesmo assim ficou errado: apertar de novo desfaria
                        falhas.append(a.slot)
                        break
                    ent.fechar()   # às vezes o COSMIC ignora o teclado virtual inteiro: cria outro
                    ent = None
                else:
                    falhas.append(a.slot)
            print(f"{time.time() - t0:5.1f}s  {a.tipo:<6} {a.slot:<16} -> {a.saida}")
        except Exception as e:
            falhas.append(a.slot)
            print(f"! {a.slot}: {e}")
    if falhas:
        print(f"layout incompleto ({', '.join(falhas)}): rode o comando de novo")
    for w in areas.values():
        c.ativar_area(w)
    c.atualizar(3)
    return ent


def gravar(c, L, saidas):
    """Mede as janelas dos slots como estão agora (tamanhos arrastados à mão), salva e refaz o pôster."""
    medidos = {}
    for s in saidas:
        rs = _rects(c, _janelas_dos_slots(c, L, s, _area_do_layout(c, s, L)))
        faltam = set(L.slots(s)) - set(rs)
        if faltam:
            print(f"{s}: faltam {', '.join(sorted(faltam))}; rode `cyberdeck` antes de gravar")
            continue
        medidos[s] = rs
        for slot, r in rs.items():
            print(f"{s:<9} {slot:<16} {r.x},{r.y} {r.w}x{r.h}")
    if medidos:
        layout.salvar_medido(medidos)
        subprocess.run(["/usr/bin/python3", str(RAIZ / "gerar_poster.py"), "--aplicar"])  # Pillow é do python do sistema, não do .venv


TRAVA = Path.home() / ".cache/cyberdeck.lock"


def _travar(arquivo):
    """Trava exclusiva: devolve o arquivo aberto (mantém a trava) ou None se outro cyberdeck já está rodando."""
    import fcntl
    f = open(arquivo, "w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        f.close()
        return None
    return f


def _rodar(argv, trava=TRAVA) -> int:
    """Roda o comando; erro vai para o log (stderr) com o traceback e o código de saída vira 1."""
    try:
        preso = _travar(trava) if trava is not None else None   # guardado: solto, o arquivo fecha e a trava cai
        if trava is not None and preso is None:
            print("cyberdeck já está rodando: ignorado")
            return 0
        if "--log" in argv:   # só agora: um 2º Super+Y não pode apagar o log de quem está rodando
            i = argv.index("--log")
            log = open(argv[i + 1], "w")
            os.dup2(log.fileno(), sys.stdout.fileno())
            os.dup2(log.fileno(), sys.stderr.fileno())
            argv = argv[:i] + argv[i + 2:]
        _main(argv)
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 0
    except Exception:
        import traceback
        traceback.print_exc()
        return 1


def main(argv):
    codigo = 1
    try:
        codigo = _rodar(argv)
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(codigo)  # evita crash do cffi ao destruir proxies


def _main(argv):
    L = layout.carregar_layout()
    c = _cosmic()
    saidas = [s for s in (layout.saidas_conectadas() or sorted(set(c.saidas.values()))) if s in L.saidas()]
    if not saidas:
        print("nenhum monitor do layout.toml conectado")
        return
    existentes, no_lugar, intrusos = set(), set(), set()
    for s in saidas:
        area = _area_do_layout(c, s, L)
        if intrusos_na_area(c, s, area, L):
            intrusos.add(s)
        geoms = {}
        for slot in list(L.slots(s)) + list(L.zonas(s)):
            js = [j for j in c.janelas.values() if e_do_slot(slot, j, area in j["areas"])]
            if js:
                existentes.add(slot)
            no_area = [j for j in js if area in j["areas"]]
            if no_area:
                no_lugar.add(slot)
                g = no_area[0]["geom"]
                geoms[slot] = g[1:] if g else None
        if desalinhada(L, s, geoms):
            intrusos.add(s)  # remonta do zero para bater com o layout
        nomes = [c.areas[w].get("nome") for w in c.areas_da_saida(s)]
        print(f"{s}: área {c.areas[area].get('nome')} de {nomes}; no lugar: {sorted(set(geoms))}")
    if "--gravar" in argv:
        return gravar(c, L, saidas)
    acoes = plano_abertura(L, existentes, no_lugar, saidas, intrusos)
    if "--plano" in argv:
        for a in acoes:
            print(a)
        print("nada a fazer: já montado" if not acoes else "(plano)")
        return
    ent = executar(c, L, acoes, saidas) if acoes else None
    ent, sobra = ajustar(c, L, saidas, ent)
    if ent:
        ent.fechar()
    if sobra:   # a divisória anda de 12 em 12 px: grava o que deu (só nesses monitores) e refaz o pôster
        gravar(c, L, sorted(sobra))
    elif not acoes and not ent:
        print("nada a fazer: já montado")


if __name__ == "__main__":
    main(sys.argv)
