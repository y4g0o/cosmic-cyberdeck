#!/usr/bin/env python3
"""HUD Cockpit de terminal do cyberdeck. stdlib apenas; coletores nunca levantam exceção.
Opções do usuário (repositórios do radar git, unidade de backup) ficam em config.toml, seção [hud].
"""
import argparse, json, os, random, re, shutil, subprocess, sys, time, urllib.request
from datetime import datetime
from pathlib import Path

JANELA = 0.2
TIMEOUT = 1
TTL_LENTO = 30.0
TTL_MEDIO = 10.0
ACID = {"fundo": "#060609", "accent": "#B8FF2E", "foco": "#7B4DFF", "roxo_profundo": "#2B1B6E",
        "circuito": "#3C7BFF", "alerta": "#FF2D55", "texto": "#E8EAF2", "muted": "#8A8CA8"}
KATAKANA = [chr(c) for c in range(0xFF66, 0xFF9E)]
SPARK = "▁▂▃▄▅▆▇█"
_BRAILLE_E = (0x00, 0x40, 0x44, 0x46, 0x47)
_BRAILLE_D = (0x00, 0x80, 0xA0, 0xB0, 0xB8)
_HIST: dict[str, list[float]] = {"cpu": [], "rede": []}
_CACHE_LENTO: dict[str, tuple[float, str]] = {}
RAIZ = Path(__file__).resolve().parent
_DADOS = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "cosmic-cyberdeck"
_CONFIG = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "cosmic-cyberdeck"
ARQ_NOTAS = _DADOS / "notas.json"   # dado seu: fora do ~/.cache, que limpadores apagam
ARQ_CMDS = _CONFIG / "comandos.json"
COMANDOS_BASE = [
    ("CYBERDECK // LAYOUT & HUD", [
        ("cyberdeck  (ou Super+Y)", "Monta o layout nos monitores e ajusta as divisórias"),
        ("cyberdeck --gravar", "Salva os tamanhos atuais das janelas e regenera o pôster"),
        ("cyberdeck --plano", "Mostra o que o cyberdeck faria sem mover janelas"),
        ("nota 'texto' | -d N", "Adiciona ou conclui lembretes rápidos no HUD Cockpit"),
        ("cmds [filtro]", "Abre este catálogo (cmds add 'nome' 'desc' salva novo)"),
        ("hud", "Recarrega o HUD no terminal atual"),
    ]),
    ("CYBERDECK // TEMA", [
        ("python3 install.py --dry-run", "Mostra tudo o que a instalação mudaria, sem tocar em nada"),
        ("python3 install.py --paleta acid", "Faz backup e aplica a paleta (tema, terminais, ícones, pôster)"),
        ("python3 install.py --uninstall", "Restaura o backup mais recente"),
        ("cyberdeck-icones", "Regera o tema de ícones e as placas"),
        ("netrun", "btop com o tema da paleta"),
    ]),
]


def _repos_padrao():
    """Este repositório + os de config.toml ([hud] repos = ["~/code/app", ...])."""
    try:
        import marca
        extras = marca.hud().get("repos", [])
    except Exception:
        extras = []
    return [("cyberdeck", RAIZ)] + [(Path(r).expanduser().name, Path(r).expanduser()) for r in extras]


def _unidade_backup() -> str:
    try:
        import marca
        return str(marca.hud().get("backup_unit", "") or "")
    except Exception:
        return ""


def _read(p):
    return Path(p).read_text()


def _run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT, **kw)


def _get(url):
    with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
        return r.read().decode()


def _seguro(padrao):
    def deco(f):
        def g(*a, **k):
            try:
                r = f(*a, **k)
                return r if isinstance(r, str) and r else padrao
            except Exception:
                return padrao
        g.__name__ = f.__name__
        return g
    return deco


def _cacheado(chave: str, fn, ttl: float = TTL_LENTO, agora=time.time) -> str:
    t = agora()
    if chave in _CACHE_LENTO and (t - _CACHE_LENTO[chave][0]) < ttl:
        return _CACHE_LENTO[chave][1]
    val = fn()
    _CACHE_LENTO[chave] = (t, val)
    return val


def _barra(pct: float, tam: int = 6) -> str:
    cheios = max(0, min(tam, round(pct / 100 * tam)))
    return "▰" * cheios + "▱" * (tam - cheios)


def _spark(valores: list[float], tam: int = 6, teto: float = 100.0) -> str:
    if not valores:
        return "▁" * tam
    vals = valores[-tam:]
    if len(vals) < tam:
        base = vals[-1]
        vals = [max(0.0, min(teto, base + ((i % 3) - 1) * (teto * 0.06))) for i in range(tam - len(vals))] + vals
    escala = max(teto, max(vals), 1.0)
    return "".join(SPARK[min(7, max(0, int(v / escala * 7.99)))] for v in vals)


def _braille_spark(valores: list[float], largura_chars: int = 6, teto: float = 100.0) -> str:
    n_amostras = largura_chars * 2
    if not valores:
        vals = [15.0, 25.0] * largura_chars
    else:
        vals = list(valores[-n_amostras:])
        if len(vals) < n_amostras:
            base = vals[-1]
            pre = [max(4.0, min(teto, base + ((i % 4) - 1.5) * (teto * 0.08))) for i in range(n_amostras - len(vals))]
            vals = pre + vals
    escala = max(teto, max(vals), 1.0)
    out = []
    for i in range(0, n_amostras, 2):
        ne = min(4, max(1 if vals[i] > 0 else 0, round(vals[i] / escala * 4)))
        nd = min(4, max(1 if vals[i + 1] > 0 else 0, round(vals[i + 1] / escala * 4)))
        out.append(chr(0x2800 | _BRAILLE_E[ne] | _BRAILLE_D[nd]))
    return "".join(out)


def _fmt_mmss(seg: float) -> str:
    s = max(0, int(seg))
    return f"{s // 60:02d}:{s % 60:02d}"


def _barra_musica(pos_s: float, dur_s: float, tam: int = 6) -> str:
    if dur_s <= 0:
        return ""
    idx = max(0, min(tam - 1, int((pos_s / dur_s) * tam)))
    trilho = "━" * idx + "●" + "─" * (tam - 1 - idx)
    return f"{_fmt_mmss(pos_s)} {trilho} {_fmt_mmss(dur_s)}"


def _cpu_tempos(texto):
    v = [int(x) for x in texto.splitlines()[0].split()[1:]]
    return sum(v[:8]), v[3] + v[4]


@_seguro("—")
def cpu(read=_read, sleep=time.sleep):
    t1, i1 = _cpu_tempos(read("/proc/stat"))
    sleep(JANELA)
    t2, i2 = _cpu_tempos(read("/proc/stat"))
    dt = t2 - t1
    if dt <= 0:
        return "—"
    pct = round(100 * (dt - (i2 - i1)) / dt)
    _HIST["cpu"] = (_HIST["cpu"] + [float(pct)])[-24:]
    return f"{pct}%"


@_seguro("—")
def ram(read=_read):
    m = {l.split(":")[0]: int(l.split()[1]) for l in read("/proc/meminfo").splitlines() if ":" in l}
    tot, av = m["MemTotal"] / 1048576, m["MemAvailable"] / 1048576
    return f"{tot - av:.1f}/{tot:.1f}G"


@_seguro("offline")
def gpu(run=_run):
    r = run(["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"])
    if r.returncode != 0:
        return "offline"
    u, t, mu, mt = [x.strip() for x in r.stdout.splitlines()[0].split(",")]
    return f"{u}% {t}°C {int(mu) / 1024:.1f}/{int(mt) / 1024:.1f}G"


@_seguro("offline")
def ollama(http_get=_get):
    ms = json.loads(http_get("http://localhost:11434/api/ps")).get("models", [])
    return "on " + (ms[0]["name"] if ms else "idle")


def _rx_tx(texto):
    rx = tx = 0
    for l in texto.splitlines()[2:]:
        nome, _, resto = l.partition(":")
        if not resto or nome.strip() == "lo":
            continue
        c = resto.split()
        rx += int(c[0])
        tx += int(c[8])
    return rx, tx


def _vel(b):
    if b < 1024:
        return f"{b:.0f}B"
    if b < 1048576:
        return f"{b / 1024:.1f}K"
    return f"{b / 1048576:.1f}M"


@_seguro("—")
def rede(read=_read, sleep=time.sleep):
    r1, t1 = _rx_tx(read("/proc/net/dev"))
    sleep(JANELA)
    r2, t2 = _rx_tx(read("/proc/net/dev"))
    rx_s, tx_s = (r2 - r1) / JANELA, (t2 - t1) / JANELA
    _HIST["rede"] = (_HIST["rede"] + [min(100.0, (rx_s + tx_s) / 10240.0)])[-24:]
    return f"↓{_vel(rx_s)} ↑{_vel(tx_s)}"


def _ha_quanto(status: str) -> str:
    """'Up 2 hours' -> '2h'; 'Up About an hour' -> '1h'; 'Up 40 seconds' -> '<1m'."""
    m = re.search(r"(\d+|an?|About an?|Less than an?) (second|minute|hour|day|week|month)", status)
    if not m:
        return ""
    n, un = m.groups()
    if un == "second" or n.startswith("Less"):
        return "<1m"
    n = n if n.isdigit() else "1"
    return n + {"minute": "m", "hour": "h", "day": "d", "week": "sem", "month": "mês"}[un]


@_seguro("—")
def docker(run=_run):
    """Containers rodando (nome + há quanto tempo): pega os esquecidos abertos."""
    r = run(["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"])
    if r.returncode != 0:
        return "—"
    itens = []
    for ln in r.stdout.splitlines():
        nome, _, status = ln.partition("\t")
        if nome:
            itens.append(f"◆ {nome} {_ha_quanto(status)}".rstrip())
    return "  ".join(itens)


@_seguro("—")
def disco(usage=shutil.disk_usage):
    u = usage("/")
    return f"{round(100 * u.used / u.total)}%"


@_seguro("—")
def disco_livre(usage=shutil.disk_usage):
    u = usage("/")
    return f"{u.free / (1024 ** 3):.0f}G"


@_seguro("—")
def backup(run=_run, agora=time.time, unidade=None):
    """Há quanto tempo a unidade de backup (config.toml [hud] backup_unit) rodou pela última vez."""
    unidade = _unidade_backup() if unidade is None else unidade
    if not unidade:
        return "—"
    r = run(["journalctl", "-u", unidade, "-n", "1", "--no-pager", "-o", "short-iso"])
    ts = datetime.fromisoformat(r.stdout.split()[0]).timestamp()
    h = max(0, (agora() - ts) / 3600)
    return f"{int(h)}h" if h < 48 else f"{int(h // 24)}d"


@_seguro("—")
def top_proc(run=_run):
    r = run(["ps", "-eo", "comm,%cpu", "--sort=-%cpu", "--no-headers"])
    if r.returncode != 0:
        return "—"
    for ln in r.stdout.splitlines():
        partes = ln.split()
        if len(partes) >= 2 and partes[0] not in ("ps", "python3"):
            return f"{partes[0][:12]} {partes[1]}%"
    return "—"


@_seguro("—")
def agentes(run=_run):
    """Detecta sessões de claude, agy e opencode (pelo cmdline completo) e se estão ativas ou aguardando."""
    r = run(["ps", "-eo", "pid,ppid,pcpu,args", "--no-headers"])
    if r.returncode != 0:
        return "—"
    procs = []
    filhos: dict[int, list[tuple[str, float]]] = {}
    for ln in r.stdout.splitlines():
        p = ln.split(None, 3)
        if len(p) >= 4 and p[0].isdigit() and p[1].isdigit():
            try:
                pid, ppid, cpu_v, args_s = int(p[0]), int(p[1]), float(p[2]), p[3]
            except ValueError:
                continue
            exe = Path(args_s.split()[0]).name.lower()
            procs.append((pid, ppid, cpu_v, exe, args_s.lower()))
            filhos.setdefault(ppid, []).append((exe, cpu_v))
    estados = {}
    for pid, _, cpu_v, exe, cmd in procs:
        if "hud.py" in cmd or "ps -eo" in cmd:
            continue
        nome = None
        if exe == "claude" or "/claude/" in cmd or cmd.startswith("claude "):
            nome = "claude"
        elif exe in ("agy", "antigravity", "antigravity-cli") or "/antigravity-cli/" in cmd or "/bin/agy" in cmd:
            nome = "agy"
        elif exe.startswith("opencode") or "/opencode" in cmd or cmd.startswith("opencode "):
            nome = "opencode"
        if not nome:
            continue
        ignorar = {"claude", "agy", "antigravity", "antigravity-cli", "opencode", "node", "cat", "sh", "fish"}
        sub = [c for c, _ in filhos.get(pid, []) if c not in ignorar]
        ativo = cpu_v > 2.5 or any(cv > 1.5 for _, cv in filhos.get(pid, [])) or bool(sub)
        est = f"⚡ ATIVO ({sub[0]})" if sub else ("⚡ ATIVO" if ativo else "● PRONTO")
        if nome not in estados or "⚡" in est:
            estados[nome] = est
    partes = [f"{k}: {estados[k]}" for k in ("claude", "agy", "opencode") if k in estados]
    return " · ".join(partes) if partes else "claude · agy · opencode [off]"


@_seguro("—")
def git_radar(run=_run, repos=None):
    """Varre os repositórios principais e mostra quantos arquivos modificados existem em cada um."""
    alvos = repos if repos is not None else _repos_padrao()
    sujos = []
    for nome, cam in alvos:
        if not (Path(cam) / ".git").exists():
            continue
        r = run(["git", "-C", str(cam), "status", "--porcelain", "-uno"])
        if r.returncode == 0:
            n = len([l for l in r.stdout.splitlines() if l.strip()])
            if n > 0:
                sujos.append(f"{nome} [{n} mod]")
    return " · ".join(sujos) if sujos else "✓ todos limpos"


def carregar_notas(arq: Path = ARQ_NOTAS) -> list[str]:
    try:
        if arq.exists():
            dados = json.loads(arq.read_text())
            return [str(x) for x in dados if str(x).strip()]
    except Exception:
        pass
    return []


def salvar_notas(lista: list[str], arq: Path = ARQ_NOTAS):
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_text(json.dumps(lista, ensure_ascii=False, indent=2))


def gerenciar_notas(args: list[str], arq: Path = ARQ_NOTAS) -> str:
    atuais = carregar_notas(arq)
    if not args or args[0] in ("-l", "--listar"):
        return "\n".join(f"[{i}] {n}" for i, n in enumerate(atuais, 1)) if atuais else "Nenhuma nota ativa."
    if args[0] in ("--limpar", "-c"):
        salvar_notas([], arq)
        return "Notas limpas."
    if args[0] in ("-d", "--del", "--feito") and len(args) >= 2 and args[1].isdigit():
        idx = int(args[1]) - 1
        if 0 <= idx < len(atuais):
            rem = atuais.pop(idx)
            salvar_notas(atuais, arq)
            return f"Concluída: {rem}"
        return f"Índice {args[1]} não encontrado."
    nova = " ".join(args).strip()
    if nova:
        atuais.append(nova)
        salvar_notas(atuais, arq)
        return f"Adicionada [{len(atuais)}]: {nova}"
    return "Nenhuma nota ativa."


def gerenciar_cmds(args: list[str], pal: dict | None = None, arq: Path = ARQ_CMDS) -> str:
    pal = pal or _paleta()
    extras: list[tuple[str, str]] = []
    try:
        if arq.exists():
            extras = [(str(k), str(v)) for k, v in json.loads(arq.read_text())]
    except Exception:
        pass
    if len(args) >= 3 and args[0] == "add":
        nome, desc = args[1].strip(), " ".join(args[2:]).strip()
        extras = [(k, v) for k, v in extras if k != nome] + [(nome, desc)]
        arq.parent.mkdir(parents=True, exist_ok=True)
        arq.write_text(json.dumps(extras, ensure_ascii=False, indent=2))
        return f"Comando salvo: {nome} — {desc}"
    if len(args) >= 2 and args[0] in ("del", "-d", "rm"):
        alvo = args[1].strip()
        extras = [(k, v) for k, v in extras if k != alvo]
        arq.parent.mkdir(parents=True, exist_ok=True)
        arq.write_text(json.dumps(extras, ensure_ascii=False, indent=2))
        return f"Comando removido: {alvo}"
    filtro = " ".join(args).lower().strip()
    grupos = list(COMANDOS_BASE)
    if extras:
        grupos.append(("CUSTOM // ADICIONADOS", extras))
    linhas = [_cor(pal["foco"], f"┏━━ // {_assinatura()} :: COMMAND DECK " + "─" * 40 + "┓")]
    for titulo, itens in grupos:
        filtrados = [(c, d) for c, d in itens if not filtro or filtro in c.lower() or filtro in d.lower() or filtro in titulo.lower()]
        if not filtrados:
            continue
        linhas.append(_cor(pal["foco"], f"  // {titulo}"))
        for cmd, desc in filtrados:
            linhas.append(f"    {_cor(pal['accent'], f'{cmd:<36}')} {_cor(pal['texto'], desc)}")
    linhas.append(_cor(pal["roxo_profundo"], "┗━━ dica: cmds <filtro>  |  cmds add 'comando' 'descrição'  |  cmds del <nome> ━━┛"))
    return "\n".join(linhas)


_ML = re.compile(r"""<(['"])(.*?)\1>""")


def _mpris(texto):
    art = re.search(r"'xesam:artist': <\[(.*?)\]>", texto)
    tit = re.search(r"'xesam:title': " + _ML.pattern, texto)
    if not tit:
        return ""
    artista = re.search(r"""(['"])(.*?)\1""", art.group(1)).group(2) if art and art.group(1) else ""
    base = f"{artista} — {tit.group(2)}" if artista else tit.group(2)
    dur = re.search(r"'mpris:length': <(?:int64 |uint64 )?(\d+)>", texto)
    pos = re.search(r"'Position': <(?:int64 )?(\d+)>", texto)
    if dur and pos:
        b = _barra_musica(int(pos.group(1)) / 1e6, int(dur.group(1)) / 1e6)
        if b:
            return f"{base}  {b}"
    return base


@_seguro("—")
def musica(run=_run):
    try:
        r = run(["playerctl", "metadata", "--format", "{{artist}} — {{title}}\t{{position}}\t{{mpris:length}}"])
        if r.returncode == 0 and r.stdout.strip():
            partes = r.stdout.strip().split("\t")
            if len(partes) == 3 and partes[1].isdigit() and partes[2].isdigit():
                b = _barra_musica(int(partes[1]) / 1e6, int(partes[2]) / 1e6)
                return f"{partes[0]}  {b}" if b else partes[0]
            return partes[0]
    except Exception:
        pass
    r = run(["gdbus", "call", "--session", "--dest", "org.mpris.MediaPlayer2.spotify",
             "--object-path", "/org/mpris/MediaPlayer2", "--method",
             "org.freedesktop.DBus.Properties.Get", "org.mpris.MediaPlayer2.Player", "Metadata"])
    return _mpris(r.stdout) if r.returncode == 0 else "—"


def alertas(dados):
    """Checagens baratas sobre os valores já coletados."""
    av = []
    try:
        if int(dados.get("disco", "").rstrip("%")) > 90:
            av.append("disco")
    except ValueError:
        pass
    m = re.search(r"(\d+)°C", dados.get("gpu", ""))
    if m and int(m.group(1)) > 80:
        av.append("gpu")
    m = re.fullmatch(r"(\d+)d", dados.get("backup", ""))
    if m and int(m.group(1)) >= 2:
        av.append("backup")
    return "! " + " ".join(av) if av else "ok"


def coletar(run=_run, http_get=_get, read=_read, usage=shutil.disk_usage, sleep=time.sleep, usar_cache: bool = False):
    fn_lento = (lambda k, f: _cacheado(k, f)) if usar_cache else (lambda k, f: f())
    fn_medio = (lambda k, f: _cacheado(k, f, ttl=TTL_MEDIO)) if usar_cache else (lambda k, f: f())
    d = {
        "cpu": cpu(read, sleep),
        "ram": ram(read),
        "rede": rede(read, sleep),
        "musica": musica(run),
        "top": top_proc(run),
        "agentes": fn_medio("agentes", lambda: agentes(run)),   # um ps completo: a cada 10 s basta
        "notas": "  ".join(f"[{i}] {n}" for i, n in enumerate(carregar_notas(), 1)),
        "gpu": fn_lento("gpu", lambda: gpu(run)),
        "ollama": fn_lento("ollama", lambda: ollama(http_get)),
        "docker": fn_lento("docker", lambda: docker(run)),
        "disco": fn_lento("disco", lambda: disco(usage)),
        "disco_livre": fn_lento("disco_livre", lambda: disco_livre(usage)),
        "backup": fn_lento("backup", lambda: backup(run)),
        "git": fn_lento("git", lambda: git_radar(run)),
    }
    d["alertas"] = alertas(d)
    return d


def _cor(hexa, texto):
    h = hexa.lstrip("#")
    return f"\x1b[38;2;{int(h[0:2], 16)};{int(h[2:4], 16)};{int(h[4:6], 16)}m{texto}\x1b[0m"


def _num_pct(s: str) -> float | None:
    m = re.match(r"(\d+(?:\.\d+)?)%", str(s))
    return float(m.group(1)) if m else None


def _ram_pct(s: str) -> float | None:
    m = re.match(r"(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)G", str(s))
    return (float(m.group(1)) / float(m.group(2)) * 100.0) if m and float(m.group(2)) > 0 else None


def _celula(rot: str, val: str, larg_col: int, pal: dict, alerta_ativo: bool = False) -> str:
    rot_p = f"{rot:<5}"
    max_v = max(0, larg_col - len(rot_p) - 1)
    if len(val) > max_v and "  " in val and ("●" in val or "━" in val):
        ini, _, fim = val.rpartition("  ")
        if len(fim) + 3 < max_v:
            val = ini[:max_v - len(fim) - 2].rstrip() + "… " + fim
    val_p = val[:max_v].ljust(max_v)
    cv = pal["alerta"] if alerta_ativo else pal["texto"]
    return _cor(pal["accent"], rot_p) + " " + _cor(cv, val_p)


def _chuva_katakana(larg: int, seed: int) -> str:
    if larg <= 0:
        return ""
    rnd = random.Random(seed)
    base = [rnd.choice(KATAKANA + ["0", "1"]) for _ in range(larg)]
    if larg >= 2:
        base[0], base[-1] = rnd.choice(KATAKANA), "0"
    return "".join(base)


def _larg_vis(s: str) -> int:
    return sum(2 if 0x2E80 <= ord(c) <= 0x9FFF else 1 for c in s)


def render(dados, pal, largura):
    g = lambda k: dados.get(k) or "—"
    cpu_p = _num_pct(g("cpu"))
    ram_p = _ram_pct(g("ram"))
    gpu_p = _num_pct(g("gpu"))
    dsk_p = _num_pct(g("disco"))

    onda_cpu = _braille_spark(_HIST["cpu"] or ([cpu_p] if cpu_p is not None else [15.0]), 5)
    onda_net = _braille_spark(_HIST["rede"] or [20.0], 4) if g("rede") != "—" else ""
    cpu_str = f"{_barra(cpu_p, 4)} {g('cpu')} {onda_cpu}" if cpu_p is not None else g("cpu")
    ram_str = f"{_barra(ram_p, 4)} {g('ram')}" if ram_p is not None else g("ram")
    gpu_str = f"{_barra(gpu_p, 4)} {g('gpu')}" if gpu_p is not None else g("gpu")
    livre = f" ({dados['disco_livre']})" if dados.get("disco_livre") and dados.get("disco_livre") != "—" else ""
    dsk_str = f"{_barra(dsk_p, 4)} {g('disco')}{livre} · bkp {g('backup')}" if dsk_p is not None else f"{g('disco')} · bkp {g('backup')}"
    net_str = f"{g('rede')} {onda_net}".strip()

    ag = dados.get("agentes")
    ol = g("ollama")
    ol_ativo = ol not in ("offline", "on idle", "—")
    base_ia = ag if (ag and ag != "—") else "claude · agy · opencode"
    ia_str = f"{base_ia} · [{ol}]" if ol_ativo else base_ia

    ice_base = g("alertas")
    top_v = dados.get("top")
    ice_str = f"{ice_base} · top: {top_v}" if ice_base == "ok" and top_v and top_v != "—" else ice_base
    alerta_ice = ice_base.startswith("!")
    dock = dados.get("docker") if dados.get("docker") not in (None, "", "—") else ""
    git_v = dados.get("git")

    if largura >= 68:
        col_e = (largura - 3) // 2
        col_d = largura - 3 - col_e
        hora = f"{datetime.now():%H:%M}"
        esq_t = f"┏━━ // {_assinatura().lower()} :: COCKPIT ─── [{hora}] "
        dir_t = " 監視中 // NODE.07 ━━┓"
        tracos = max(1, largura - _larg_vis(esq_t) - _larg_vis(dir_t))
        topo = _cor(pal["foco"], (esq_t + "─" * tracos + dir_t)[:largura])
        sep = _cor(pal["roxo_profundo"], "│")
        git_col = git_v if git_v and git_v != "—" else "✓ limpos"
        notas_v = dados.get("notas", "").strip()
        pares = [
            (("SYS", f"{cpu_str} · {ram_str}", False), ("NET", net_str, False)),
            (("VRAM", gpu_str, False), ("IA", ia_str, False)),
            (("DISK", dsk_str, False), ("ICE", ice_str, alerta_ice)),
            (("GIT", git_col, False), ("♪", g("musica"), False)),
        ]
        if dock:
            n = dock.count("◆")
            pares.append((("DOCK", dock, False), ("STOP", f"{n} aberto{'s' if n > 1 else ''} · docker stop NOME", False)))
        if notas_v:
            pares.append((("NOTA", notas_v, False), ("CMD", "nota 'txt' | nota -d N", False)))
        corpo = [topo]
        for (re_, ve, ae), (rd, vd, ad) in pares:
            ce = _celula(re_, ve, col_e, pal, ae)
            cd = _celula(rd, vd, col_d, pal, ad)
            corpo.append(f"{ce} {sep} {cd}")
        ch_larg = max(2, largura - 18)
        chuva = _chuva_katakana(ch_larg, int(time.time()))
        corpo.append(_cor(pal["roxo_profundo"], f"┗━━ 0x7F3A :: {chuva} ━━┛"[:largura]))
        return "\n".join(corpo)

    linhas = [
        ("SYS", f"cpu {cpu_str} · ram {g('ram')}"),
        ("VRAM", gpu_str),
        ("IA", ia_str),
        ("NET", net_str),
        ("DISK", dsk_str),
        ("♪", g("musica")),
        ("ICE", ice_str),
    ]
    if dock:
        linhas.append(("DOCK", dock))
    saida = [_cor(pal["foco"], f"▌{_assinatura().lower()} // hud {datetime.now():%H:%M}"[:largura])]
    for rot, val in linhas:
        val = val[:max(0, largura - len(rot) - 1)]
        cv = pal["alerta"] if rot == "ICE" and alerta_ice else pal["texto"]
        saida.append(_cor(pal["accent"], rot) + " " + _cor(cv, val))
    saida.append(_cor(pal["roxo_profundo"], _chuva_katakana(largura, int(time.time()))))
    return "\n".join(saida)


def _assinatura():
    try:
        import marca
        return marca.assinatura()
    except Exception:
        return "CYBERDECK"


def _paleta():
    try:
        import paleta
        return paleta.carregar()
    except Exception:
        return ACID


def _marca_paleta():
    try:
        return (Path(__file__).resolve().parent / "paletas/ATIVA").stat().st_mtime
    except OSError:
        return None


def paleta_atual(pal: dict, marca, nova_marca, carregar=_paleta):
    """Recarrega a paleta só quando paletas/ATIVA mudou (aplicar.py sempre o reescreve)."""
    return (carregar(), nova_marca) if nova_marca != marca else (pal, marca)


def painel_ansi(texto: str, linhas_terminal: int | None = None) -> str:
    """Redesenha o HUD nas primeiras linhas sem mexer no cursor do shell. Com linhas_terminal, reaplica a
    região de rolagem (o terminal a zera em redimensionamento e Ctrl+L)."""
    linhas = texto.splitlines()
    regiao = f"\x1b[{len(linhas) + 1};{linhas_terminal}r" if linhas_terminal else ""
    corpo = "".join(f"\x1b[{i};1H\x1b[2K{ln}" for i, ln in enumerate(linhas, 1))
    return "\x1b7" + regiao + corpo + "\x1b8"


def shell_em_primeiro_plano(fd: int, shell_pid: int, tcgetpgrp=None, getpgid=None) -> bool:
    """True quando o terminal está no prompt (o shell é o grupo em primeiro plano), não num programa."""
    return (tcgetpgrp or os.tcgetpgrp)(fd) == (getpgid or os.getpgid)(shell_pid)


def linhas_do_painel(dados: dict, largura: int) -> int:
    return len(render(dados, _paleta(), largura).splitlines())


def main(argv=None, coletar=coletar, pal=None, largura=None):
    lista_args = list(sys.argv[1:] if argv is None else argv)
    if lista_args and lista_args[0] == "--gerenciar-nota":
        print(gerenciar_notas(lista_args[1:]))
        return 0
    if lista_args and lista_args[0] == "--cmds":
        print(gerenciar_cmds(lista_args[1:], pal))
        return 0
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--uma-vez", action="store_true")
    g.add_argument("--loop", type=float, metavar="SEGUNDOS")
    g.add_argument("--painel", type=float, metavar="SEGUNDOS", help="HUD fixo no topo (região de rolagem)")
    g.add_argument("--linhas", action="store_true", help="quantas linhas o HUD ocupa")
    a = ap.parse_args(lista_args)
    pal = pal or _paleta()
    larg = lambda: largura or shutil.get_terminal_size((60, 20)).columns
    if a.uma_vez:
        print(render(coletar(), pal, larg()))
        return 0
    if a.linhas:
        vazio = {k: "—" for k in ("cpu", "ram", "gpu", "ollama", "rede", "disco", "backup", "musica", "alertas")}
        print(linhas_do_painel(vazio, larg()))
        return 0
    if a.painel:
        try:
            shell = os.getppid()
            marca = _marca_paleta()
            meu_mtime = Path(__file__).resolve().stat().st_mtime
            while True:
                if Path(__file__).resolve().stat().st_mtime != meu_mtime:
                    os.execv(sys.executable, [sys.executable, str(Path(__file__).resolve())] + lista_args)
                pal, marca = paleta_atual(pal, marca, _marca_paleta())
                if shell_em_primeiro_plano(sys.stdout.fileno(), shell):  # pausa com claude/less/vim rodando
                    try:
                        d = coletar(usar_cache=True)
                    except TypeError:
                        d = coletar()
                    sys.stdout.write(painel_ansi(render(d, pal, larg()), shutil.get_terminal_size((60, 24)).lines))
                    sys.stdout.flush()
                time.sleep(a.painel)
        except (KeyboardInterrupt, OSError):  # terminal fechado -> sai
            return 0
    try:
        while True:
            print("\x1b[H\x1b[J" + render(coletar(), pal, larg()), end="", flush=True)
            time.sleep(a.loop)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
