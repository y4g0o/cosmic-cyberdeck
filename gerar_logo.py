"""Gera o logo do fastfetch: fluxo de dados (katakana + bits) como um quadro de chuva digital."""
import pathlib
import random

import marca

COLS, ROWS = 14, 11
OUT = pathlib.Path.home() / ".config/fastfetch/logo.txt"
# $5 branco, $1 accent, $2 foco, $4 cinza (cores definidas no config.jsonc)
KANA = "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝｦ"

rnd = random.Random(2077)
cabeca = [rnd.randint(2, ROWS + 3) for _ in range(COLS)]  # linha da cabeça de cada coluna
cauda = [rnd.randint(4, 9) for _ in range(COLS)]


def cor(dist):
    if dist == 0:
        return "$5"
    if dist <= 2:
        return "$1"
    if dist <= 5:
        return "$2"
    return "$4"


linhas = []
for r in range(ROWS):
    txt, atual = " ", None
    for c in range(COLS):
        dist = cabeca[c] - r
        if dist < 0 or dist > cauda[c]:
            txt += "  "
            continue
        ch = rnd.choice("01") if rnd.random() < 0.3 else rnd.choice(KANA)
        k = cor(dist)
        if k != atual:
            txt += k
            atual = k
        txt += ch + " "
    linhas.append(txt.rstrip())

linhas += [
    "",
    f"$3▓▒░$1 NETRUNNER ID ::$2 {marca.assinatura()} $3░▒▓",
]
OUT.write_text("\n".join(linhas) + "\n")
print(OUT)
