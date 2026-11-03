#!/bin/bash
# Login: first the maintenance (Spicetify, icons, COSMIC theme, sounds, boot), then assemble the layout.
# Sequential on purpose: Spicetify patches Spotify, so the layout must not open Spotify before it finishes.
# Enabled by `python3 install.py --autostart`; disabled by `python3 install.py --uninstall`.
RAIZ="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
sleep 8   # let the session finish starting
bash "$RAIZ/manutencao.sh"
PY="$RAIZ/.venv/bin/python"; [ -x "$PY" ] || exit 0   # no Wayland bindings: maintenance only
exec "$PY" "$RAIZ/montar.py" --log "$HOME/.cache/cyberdeck.log"   # the log is only cleared after the lock
