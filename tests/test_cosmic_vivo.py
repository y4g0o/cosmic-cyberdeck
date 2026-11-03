"""Teste com o compositor de verdade (pula fora da sessão gráfica). Roda no .venv, que tem o pywayland."""
import os
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
PY = RAIZ / ".venv/bin/python"


@pytest.mark.wayland
@pytest.mark.skipif(not os.environ.get("WAYLAND_DISPLAY") or not PY.exists(),
                    reason="needs a live COSMIC Wayland session and .venv with pywayland")
def test_registro_sobrevive_a_coleta_de_lixo():
    # o pywayland acha o display pelos WlRegistry vivos; se forem coletados, janelas novas são descartadas
    # ("Cannot find display") e o cyberdeck acha que todos os apps estão fechados
    codigo = ("import gc, sys; sys.path.insert(0, 'wl'); from cosmic import Cosmic; "
              "from pywayland.protocol.wayland import WlRegistry; c = Cosmic(); gc.collect(); "
              "print(len(WlRegistry.registry), flush=True); import os; os._exit(0)")
    r = subprocess.run([str(PY), "-c", codigo], cwd=RAIZ, capture_output=True, text=True, timeout=20)
    assert r.returncode == 0, r.stderr
    assert int(r.stdout.split()[-1]) > 0
