"""Teclado e mouse virtuais via /dev/uinput (só biblioteca padrão): apertam atalhos do COSMIC que não têm
protocolo Wayland, como redimensionar (Super+R segurado + setas) e girar a divisão (Super+O). O compositor
recebe como dispositivos de verdade. Requer permissão de escrita em /dev/uinput (ACL do usuário).

O COSMIC aplica esses atalhos no monitor onde está o cursor, por isso o mouse: ele só empurra o cursor
para a borda do monitor certo."""
import fcntl
import os
import struct
import time
from contextlib import contextmanager

TECLAS = {"super": 125, "shift": 42, "r": 19, "o": 24, "esc": 1, "enter": 28,
          "up": 103, "down": 108, "left": 105, "right": 106}
_EV_SYN, _EV_KEY, _EV_REL = 0, 1, 2
_BTN_LEFT = 0x110
_UI_SET_EVBIT, _UI_SET_KEYBIT, _UI_SET_RELBIT = 0x40045564, 0x40045565, 0x40045566
_UI_DEV_CREATE, _UI_DEV_DESTROY = 0x5501, 0x5502


def _evento(tipo: int, codigo: int, valor: int) -> bytes:
    return struct.pack("llHHi", 0, 0, tipo, codigo, valor)   # struct input_event (o kernel preenche a hora)


class _Dispositivo:
    def __init__(self, nome: bytes, produto: int, configurar, caminho="/dev/uinput", espera=0.8):
        self.fd = os.open(caminho, os.O_WRONLY | os.O_NONBLOCK)
        configurar(self.fd)
        # struct uinput_user_dev: nome, input_id (barramento USB), ff_effects_max, 4 x 64 eixos zerados
        os.write(self.fd, struct.pack("80sHHHHi", nome, 0x03, 0x1, produto, 1, 0) + bytes(4 * 64 * 4))
        fcntl.ioctl(self.fd, _UI_DEV_CREATE)
        time.sleep(espera)   # o compositor precisa enxergar o dispositivo novo

    def _enviar(self, *eventos):
        os.write(self.fd, b"".join(_evento(*e) for e in eventos) + _evento(_EV_SYN, 0, 0))

    def fechar(self):
        fcntl.ioctl(self.fd, _UI_DEV_DESTROY)
        os.close(self.fd)


def _cfg_teclado(fd):
    fcntl.ioctl(fd, _UI_SET_EVBIT, _EV_KEY)
    for k in range(1, 249):   # teclado completo: com poucas teclas o udev não o trata como teclado
        fcntl.ioctl(fd, _UI_SET_KEYBIT, k)


def _cfg_mouse(fd):
    fcntl.ioctl(fd, _UI_SET_EVBIT, _EV_KEY)
    fcntl.ioctl(fd, _UI_SET_KEYBIT, _BTN_LEFT)   # sem botão o udev não o trata como mouse
    fcntl.ioctl(fd, _UI_SET_EVBIT, _EV_REL)
    for eixo in (0, 1):
        fcntl.ioctl(fd, _UI_SET_RELBIT, eixo)


class Teclado(_Dispositivo):
    def __init__(self, **kw):
        super().__init__(b"cyberdeck-teclado", 0x1, _cfg_teclado, **kw)

    def _tecla(self, codigo: int, valor: int):
        self._enviar((_EV_KEY, codigo, valor))
        time.sleep(0.03)

    @contextmanager
    def segurando(self, combo: str):
        """Mantém as teclas de `combo` ("super+r") apertadas; solta sempre, mesmo com erro."""
        ks = [TECLAS[k] for k in combo.split("+")]
        apertadas = []
        try:
            for k in ks:
                self._tecla(k, 1)
                apertadas.append(k)
            time.sleep(0.15)
            yield
        finally:
            for k in reversed(apertadas):
                self._tecla(k, 0)

    def tocar(self, tecla: str, pausa=0.2):
        self._tecla(TECLAS[tecla], 1)
        self._tecla(TECLAS[tecla], 0)
        time.sleep(pausa)

    def atalho(self, combo: str, pausa=0.2):
        with self.segurando(combo):
            pass
        time.sleep(pausa)


class Mouse(_Dispositivo):
    def __init__(self, **kw):
        super().__init__(b"cyberdeck-mouse", 0x2, _cfg_mouse, **kw)

    def empurrar(self, dx: int, dy: int = 0, vezes=40):
        """Movimento relativo repetido: o bastante para encostar o cursor numa borda."""
        for _ in range(vezes):
            self._enviar((_EV_REL, 0, dx), (_EV_REL, 1, dy))
            time.sleep(0.005)
