#!/bin/bash
# Manutenção do cyberdeck no login: só age se algo mudou (custo ~10 ms quando não há nada a fazer).
RAIZ="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
EST="${XDG_CACHE_HOME:-$HOME/.cache}/cosmic-cyberdeck"; mkdir -p "$EST"
log() { echo "$(date '+%F %T') $*" >> "$EST/manutencao.log"; }

# 1) Spotify sem o tema? (depois de uma atualização volta o xpui.spa original) reaplica o Spicetify.
#    O backup antigo é da versão anterior: se o `backup` recusar, limpa e faz de novo a partir da versão nova.
ver=$(dpkg-query -W -f='${Version}' spotify-client 2>/dev/null)
spice=~/.spicetify/spicetify
if [ -n "$ver" ] && [ -x "$spice" ] && [ -f /usr/share/spotify/Apps/xpui.spa ]; then
    if [ -w /usr/share/spotify/Apps ]; then
        if "$spice" backup apply --no-restart >> "$EST/manutencao.log" 2>&1 \
           || { "$spice" clear --no-restart >> "$EST/manutencao.log" 2>&1 \
                && "$spice" backup apply --no-restart >> "$EST/manutencao.log" 2>&1; }; then
            log "spicetify reaplicado ($ver)"
        else
            log "spicetify falhou ($ver)"
            notify-send -i spotify "cyberdeck" "Não consegui reaplicar o tema do Spotify. Veja $EST/manutencao.log"
        fi
    else
        log "sem permissão em /usr/share/spotify"
        notify-send -i spotify "cyberdeck" "Spotify atualizou sem o tema. Rode uma vez: python3 $RAIZ/install.py --spotify-hook (mostra o comando com sudo)"
    fi
fi

# 2) Apps instalados/removidos? recolore só os ícones que faltam
hash=$(ls -l --time-style=+%s /usr/share/applications ~/.local/share/applications \
       ~/.local/share/flatpak/exports/share/applications /var/lib/flatpak/exports/share/applications 2>/dev/null | md5sum)
if [ "$hash" != "$(cat "$EST/apps.hash" 2>/dev/null)" ]; then
    python3 "$RAIZ"/gerar_icones.py --incremental >> "$EST/manutencao.log" 2>&1 \
      && gtk-update-icon-cache -f -q ~/.local/share/icons/Papirus-cyberdeck \
      && gtk-update-icon-cache -f -q ~/.local/share/icons/Papirus-Dark-cyberdeck \
      && echo "$hash" > "$EST/apps.hash" && log "ícones verificados"
fi

# 3) COSMIC atualizou e trouxe chave nova no tema (ou a paleta saiu do formato)? reconstrói o tema
if ! python3 "$RAIZ"/verificar_tema.py >> "$EST/manutencao.log" 2>&1; then
    python3 "$RAIZ"/verificar_tema.py --consertar >> "$EST/manutencao.log" 2>&1 && log "tema do COSMIC consertado"
fi

# 4) sons: alguma atualização voltou o tema de sons ao padrão?
if [ -d ~/.local/share/sounds/cyberdeck ] && [ "$(gsettings get org.gnome.desktop.sound theme-name)" != "'cyberdeck'" ]; then
    gsettings set org.gnome.desktop.sound theme-name cyberdeck && log "tema de sons reposto"
fi

# 5) tela de boot: uma atualização do Plymouth trocou o tema? (consertar precisa de sudo: só avisa)
if [ -d /usr/share/plymouth/themes/cyberdeck ] && [ "$(readlink -f /usr/share/plymouth/themes/default.plymouth)" != /usr/share/plymouth/themes/cyberdeck/cyberdeck.plymouth ]; then
    log "tela de boot voltou ao padrão"
    notify-send "cyberdeck" "A tela de boot voltou ao padrão. Rode: sudo bash $RAIZ/saida/plymouth/INSTALAR-BOOT.sh"
fi
