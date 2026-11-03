; cyberdeck — gerado de paletas/
[general]
bars = 0
bar_width = 1
bar_spacing = 1
framerate = 30   ; metade da CPU, imperceptível
sleep_timer = 3  ; para de desenhar após 3 s de silêncio

[output]
channels = stereo   ; espelhado: graves no centro, agudos nas pontas

[input]
method = pulse
source = auto   ; monitor da saída padrão (o que está tocando)

[color]
; cor por nome = cor do tema do terminal (magenta = roxo da paleta). Hex não funciona aqui: o cava 0.7.4
; redefine a paleta do terminal (initc) e o cosmic-term ignora, mostrando azul/verde puros.
gradient = 0
foreground = 'magenta'

[smoothing]
monstercat = 0
noise_reduction = 77
