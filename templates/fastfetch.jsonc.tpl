{
  "$schema": "https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json",
  "logo": {
    "type": "file",
    "source": "~/.config/fastfetch/logo.txt",
    "color": { "1": "{{accent}}", "2": "{{foco}}", "3": "{{alerta}}", "4": "{{ansi_8}}", "5": "{{quase_branco}}" },
    "padding": { "right": 3 }
  },
  "display": {
    "separator": "  ",
    "color": { "keys": "{{accent}}", "title": "{{foco}}" }
  },
  "modules": [
    { "type": "custom", "format": "\u001b[38;2;255;0;60m┏━━━━━━━━━━ SYS.DIAGNOSTIC ━━━━━━━━━━┓" },
    { "type": "title", "key": "┃ NETRUNNER" },
    { "type": "os", "key": "┃ OS       " },
    { "type": "kernel", "key": "┃ KERNEL   " },
    { "type": "de", "key": "┃ DE       " },
    { "type": "shell", "key": "┃ SHELL    " },
    { "type": "cpu", "key": "┃ CPU      " },
    { "type": "gpu", "key": "┃ GPU      " },
    { "type": "memory", "key": "┃ RAM      " },
    { "type": "uptime", "key": "┃ UPTIME   " },
    { "type": "custom", "format": "\u001b[38;2;255;0;60m┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛" },
    { "type": "colors", "symbol": "block" }
  ]
}
