"""Layout do cyberdeck: retângulos dos slots (janelas) e zonas (janelas-fantasma) por monitor.

Fonte de verdade: layout.toml. A árvore descreve as divisões ao meio do tiling do COSMIC:
H(a, b) = lado a lado, V(a, b) = empilhado. Coordenadas em px locais de cada saída.
"""
import re
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parent / "layout.toml"
MEDIDO = Path(__file__).resolve().parent / "layout-medido.toml"   # gerado por `cyberdeck --gravar` (tamanhos ajustados à mão)


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    w: int
    h: int


def _parse(expr: str):
    """'H(V(a,b),c)' -> ('H', [('V', ['a', 'b']), 'c'])"""
    expr = expr.replace(" ", "")
    pos = 0

    def no():
        nonlocal pos
        m = re.match(r"([HV])\(", expr[pos:])
        if m:
            pos += 2
            filhos = [no()]
            while expr[pos] == ",":
                pos += 1
                filhos.append(no())
            assert expr[pos] == ")", expr
            pos += 1
            return (m.group(1), filhos)
        m = re.match(r"[a-z_]+", expr[pos:])
        pos += m.end()
        return m.group(0)

    return no()


def _dividir(no, r: Rect, gap: int, saida: dict, divisoes: list | None = None, raiz: Rect | None = None):
    """Como o tiling do COSMIC: divide a região exatamente ao meio (sem descontar vão); cada janela final
    é a região recuada `gap` nas bordas externas (as da raiz) e `gap//2` nas internas."""
    raiz = raiz or r
    if isinstance(no, str):
        e = gap if r.x == raiz.x else gap // 2
        t = gap if r.y == raiz.y else gap // 2
        d = gap if r.x + r.w == raiz.x + raiz.w else gap // 2
        b = gap if r.y + r.h == raiz.y + raiz.h else gap // 2
        saida[no] = Rect(r.x + e, r.y + t, r.w - e - d, r.h - t - b)
        return
    direcao, (a, b) = no
    if divisoes is not None:
        divisoes.append((direcao, r))
    if direcao == "H":
        wa = r.w // 2
        _dividir(a, Rect(r.x, r.y, wa, r.h), gap, saida, divisoes, raiz)
        _dividir(b, Rect(r.x + wa, r.y, r.w - wa, r.h), gap, saida, divisoes, raiz)
    else:
        ha = r.h // 2
        _dividir(a, Rect(r.x, r.y, r.w, ha), gap, saida, divisoes, raiz)
        _dividir(b, Rect(r.x, r.y + ha, r.w, r.h - ha), gap, saida, divisoes, raiz)


class Layout:
    def __init__(self, dados: dict, medido: dict | None = None):
        g = dados["geral"]
        self.painel = g["painel"]
        self.gap_externo = g["gap_externo"]
        self.gap_interno = g["gap_interno"]
        self._saidas = {}
        for nome, s in dados["saidas"].items():
            area = Rect(self.gap_externo, self.painel + self.gap_externo,
                        s["largura"] - 2 * self.gap_externo, s["altura"] - self.painel - 2 * self.gap_externo)
            rects, divisoes = {}, []
            _dividir(_parse(s["arvore"]), area, self.gap_interno, rects, divisoes)
            zonas = set(s.get("zonas", []))
            ajustes = {k: Rect(*v) for k, v in (medido or {}).get(nome, {}).items() if k in rects}
            rects.update(ajustes)
            self._saidas[nome] = {
                "medido": bool(ajustes),
                "tamanho": (s["largura"], s["altura"]),
                "slots": {k: v for k, v in rects.items() if k not in zonas},
                "zonas": {k: v for k, v in rects.items() if k in zonas},
                "arvore": s["arvore"],
                "divisoes": divisoes,
            }

    def saidas(self) -> list[str]:
        return list(self._saidas)

    def tamanho(self, saida: str) -> tuple[int, int]:
        return self._saidas[saida]["tamanho"]

    def slots(self, saida: str) -> dict[str, Rect]:
        return dict(self._saidas[saida]["slots"])

    def zonas(self, saida: str) -> dict[str, Rect]:
        return dict(self._saidas[saida]["zonas"])

    def tem_medido(self, saida: str) -> bool:
        return self._saidas[saida]["medido"]

    def arvore(self, saida: str):
        return _parse(self._saidas[saida]["arvore"])

    def divisoes(self, saida: str) -> list[tuple[str, Rect]]:
        """(direção, região dividida) de cada nó interno, na ordem da árvore."""
        return list(self._saidas[saida]["divisoes"])


def carregar_layout(arquivo: Path = ARQUIVO, medido: Path | None = MEDIDO) -> Layout:
    return Layout(tomllib.loads(arquivo.read_text()), _ler_medido(medido))


def _ler_medido(arquivo: Path | None) -> dict:
    return tomllib.loads(arquivo.read_text()) if arquivo and arquivo.exists() else {}


def esticar_para_as_bordas(rects: dict, largura: int, altura: int, painel: int, interno: int,
                           antigo: int, novo: int) -> dict:
    """Tamanhos gravados à mão depois de mudar o vão externo: a janela que encosta numa borda da tela
    estica (ou encolhe) por aquele lado; as divisórias entre as janelas ficam onde o usuário deixou."""
    d = antigo - novo
    esq, topo = antigo + interno, painel + antigo + interno
    dir_, base = largura - antigo - interno, altura - antigo - interno
    out = {}
    for n, r in rects.items():
        x, y, w, h = r.x, r.y, r.w, r.h
        if r.x + r.w == dir_:
            w += d
        if r.y + r.h == base:
            h += d
        if r.x == esq:
            x, w = x - d, w + d
        if r.y == topo:
            y, h = y - d, h + d
        out[n] = Rect(x, y, w, h)
    return out


def salvar_medido(rects: dict[str, dict[str, Rect]], arquivo: Path = MEDIDO):
    """Grava os retângulos medidos por saída, mantendo as saídas que não vieram em `rects`."""
    dados = {**_ler_medido(arquivo), **{s: {k: [r.x, r.y, r.w, r.h] for k, r in rs.items()} for s, rs in rects.items()}}
    linhas = ["# gerado por `cyberdeck --gravar`: tamanhos ajustados à mão (apague para voltar às metades do layout.toml)"]
    for s, rs in dados.items():
        linhas.append(f'\n["{s}"]')
        linhas += [f"{k} = {list(v)}" for k, v in rs.items()]
    Path(arquivo).write_text("\n".join(linhas) + "\n")


def _randr() -> str:
    return subprocess.run(["cosmic-randr", "list"], capture_output=True, text=True, timeout=3).stdout


def saidas_conectadas(listar=_randr) -> list[str]:
    try:
        texto = re.sub(r"\x1b\[[0-9;]*m", "", listar())
    except Exception:
        return []
    return re.findall(r"^(\S+) \(enabled\)", texto, re.M)


def posicoes(listar=_randr) -> dict[str, tuple[int, int]]:
    """Posição (x, y) de cada monitor ligado, no espaço global do COSMIC."""
    try:
        texto = re.sub(r"\x1b\[[0-9;]*m", "", listar())
    except Exception:
        return {}
    blocos = re.split(r"(?m)^(?=\S)", texto)   # um bloco por monitor: começa na linha sem recuo
    pos = {}
    for b in blocos:
        m = re.match(r"(\S+) \(enabled\)", b)
        p = re.search(r"^\s*Position: (-?\d+),(-?\d+)", b, re.M)
        if m and p:
            pos[m.group(1)] = (int(p.group(1)), int(p.group(2)))
    return pos
