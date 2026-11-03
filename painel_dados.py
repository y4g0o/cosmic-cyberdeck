"""Coleta dos dados do painel de arte (reaproveita os coletores do HUD). Nunca levanta exceção."""
import glob as _glob
import re
import socket
import subprocess
import time
from pathlib import Path

import hud

_MPRIS = ["gdbus", "call", "--session", "--dest", "org.mpris.MediaPlayer2.spotify", "--object-path",
          "/org/mpris/MediaPlayer2", "--method", "org.freedesktop.DBus.Properties.Get", "org.mpris.MediaPlayer2.Player"]
_DIAS = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]


def progresso(saida_pos: str, saida_meta: str) -> float:
    try:
        pos = int(re.search(r"int64 (\d+)", saida_pos).group(1))
        total = int(re.search(r"mpris:length': <u?int64 (\d+)", saida_meta).group(1))
        return min(1.0, pos / total) if total else 0.0
    except Exception:
        return 0.0


def temp_cpu(glob=_glob.glob, ler=lambda p: Path(p).read_text()) -> str:
    try:
        for nome in glob("/sys/class/hwmon/hwmon*/name"):
            if ler(nome).strip() in ("coretemp", "k10temp"):
                milli = int(ler(nome.replace("name", "temp1_input")).strip())
                return f"{round(milli / 1000)}°C"
    except Exception:
        pass
    return "—"


def temp_gpu(gpu_hud: str) -> str:
    m = re.search(r"(\d+)°C", gpu_hud or "")
    return f"{m.group(1)}°C" if m else "—"


def ip_local(sock=socket.socket) -> str:
    try:
        s = sock(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("1.1.1.1", 80))  # UDP sem enviar pacote: só descobre a interface de saída
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "—"


def _run(args) -> str:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=1).stdout
    except Exception:
        return ""


def coletar() -> dict:
    agora = time.localtime()
    base = hud.coletar()
    return {
        "hora": time.strftime("%H:%M", agora),
        "data": f"{_DIAS[agora.tm_wday]} {time.strftime('%d.%m', agora)}",
        "musica": base.get("musica", "—"),
        "progresso": progresso(_run(_MPRIS + ["Position"]), _run(_MPRIS + ["Metadata"])),
        "ip": ip_local(),
        "rede": base.get("rede", ""),
        "temp": f"cpu {temp_cpu()} · gpu {temp_gpu(base.get('gpu', ''))}",
        "ia": base.get("ollama", "—"),
        "backup": base.get("backup", "—"),
        "alertas": base.get("alertas", "—"),
    }
