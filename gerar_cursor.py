"""Gera o cursor 'Bibata-Modern-cyberdeck': Bibata Amber com o âmbar trocado pela matiz do accent da paleta."""
import colorsys
import pathlib
import shutil
import struct

import numpy as np

import paleta

ICONS = pathlib.Path.home() / ".local/share/icons"
ORIGEM = next((d / "Bibata-Modern-Amber" for d in (ICONS, pathlib.Path("/usr/share/icons"))
               if (d / "Bibata-Modern-Amber").is_dir()), ICONS / "Bibata-Modern-Amber")
DESTINO = ICONS / "Bibata-Modern-cyberdeck"
HUE_ALVO = colorsys.rgb_to_hsv(*(x / 255 for x in paleta.hex_rgb(paleta.carregar()["accent"])))[0]  # matiz do accent
IMAGEM = 0xFFFD0002


def recolorir_pixels(px):
    """px: uint32 ARGB pré-multiplicado. Troca a matiz dos tons âmbar/laranja."""
    a = ((px >> 24) & 0xFF).astype(np.float32)
    rgb = np.stack([(px >> 16) & 0xFF, (px >> 8) & 0xFF, px & 0xFF], -1).astype(np.float32)
    vis = a > 0
    rgb[vis] = rgb[vis] / a[vis, None]  # despré-multiplica -> 0..1
    mx, mn = rgb.max(-1), rgb.min(-1)
    delta = mx - mn
    s = np.where(mx > 0, delta / np.maximum(mx, 1e-6), 0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    h = np.zeros_like(mx)
    m = (delta > 0) & (mx == r)
    h[m] = ((g[m] - b[m]) / delta[m]) % 6
    m2 = (delta > 0) & (mx == g)
    h[m2] = (b[m2] - r[m2]) / delta[m2] + 2
    h /= 6
    alvo = vis & (s > 0.25) & (h >= 0.04) & (h < 0.2)  # âmbar/laranja (preserva vermelho)
    # HSV -> RGB com a nova matiz, mesma saturação e valor
    v = mx[alvo]
    sat = s[alvo]
    i = int(HUE_ALVO * 6)
    f = HUE_ALVO * 6 - i
    p, q, t = v * (1 - sat), v * (1 - sat * f), v * (1 - sat * (1 - f))
    novo = {0: (v, t, p), 1: (q, v, p), 2: (p, v, t), 3: (p, q, v), 4: (t, p, v), 5: (v, p, q)}[i]
    rgb[alvo] = np.stack(novo, -1)
    rgb = np.clip(rgb * a[..., None], 0, 255).astype(np.uint32)  # pré-multiplica de novo
    out = (a.astype(np.uint32) << 24) | (rgb[..., 0] << 16) | (rgb[..., 1] << 8) | rgb[..., 2]
    return np.where(vis, out, px).astype(np.uint32)


def recolorir_arquivo(f):
    dados = bytearray(f.read_bytes())
    _, hsize, _, ntoc = struct.unpack_from("<4sIII", dados, 0)
    for k in range(ntoc):
        tipo, _, pos = struct.unpack_from("<III", dados, hsize + 12 * k)
        if tipo != IMAGEM:
            continue
        chsize, _, _, _, w, h = struct.unpack_from("<IIIIII", dados, pos)
        ini = pos + chsize
        px = np.frombuffer(bytes(dados[ini:ini + 4 * w * h]), dtype="<u4")
        dados[ini:ini + 4 * w * h] = recolorir_pixels(px).astype("<u4").tobytes()
    f.write_bytes(bytes(dados))


if __name__ == "__main__":
    if not ORIGEM.is_dir():
        print("Bibata-Modern-Amber não encontrado (~/.local/share/icons ou /usr/share/icons): cursor pulado")
        raise SystemExit(0)
    if DESTINO.exists():
        shutil.rmtree(DESTINO)
    shutil.copytree(ORIGEM, DESTINO, symlinks=True)
    n = 0
    for f in (DESTINO / "cursors").iterdir():
        if f.is_file() and not f.is_symlink():
            recolorir_arquivo(f)
            n += 1
    for nome in ("index.theme", "cursor.theme"):
        p = DESTINO / nome
        p.write_text(p.read_text().replace("Bibata-Modern-Amber", "Bibata-Modern-cyberdeck"))
    print(n, "cursores recoloridos")
