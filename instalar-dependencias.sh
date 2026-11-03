#!/bin/bash
# Optional third-party tools the theme can style. Each step asks first; nothing here touches the theme itself.
# Needs sudo (apt) and network (GitHub releases / Spicetify installer). Usage: bash instalar-dependencias.sh
set -e
mkdir -p "$HOME/.local/bin"
pergunta() { read -r -p "$1 [y/N] " r; [ "$r" = y ] || [ "$r" = Y ]; }

if pergunta ">> Install cava, fish, btop, Papirus icons and Python deps (Pillow, numpy) with apt?"; then
    sudo apt install -y cava fish btop papirus-icon-theme python3-pil python3-numpy fonts-noto-cjk
fi

if pergunta ">> Install starship (prompt) into ~/.local/bin?"; then
    curl -sfL https://github.com/starship/starship/releases/latest/download/starship-x86_64-unknown-linux-musl.tar.gz \
        | tar xz -C "$HOME/.local/bin" starship
fi

if pergunta ">> Install fastfetch into ~/.local/bin?"; then
    tmp=$(mktemp -d)
    curl -sfL https://github.com/fastfetch-cli/fastfetch/releases/latest/download/fastfetch-linux-amd64.tar.gz | tar xz -C "$tmp"
    cp "$(find "$tmp" -path '*bin/fastfetch' | head -1)" "$HOME/.local/bin/"
    rm -rf "$tmp"
fi

if pergunta ">> Install Spicetify (Spotify theme)? Close Spotify first."; then
    curl -fsSL https://raw.githubusercontent.com/spicetify/cli/main/install.sh | sh
    export PATH="$HOME/.spicetify:$PATH"
    # only the Apps folder becomes yours; /usr/share/spotify stays root-owned (no world-writable folders)
    sudo chown -R "$(id -un):$(id -gn)" /usr/share/spotify/Apps
    spicetify config current_theme cyberdeck color_scheme Base inject_css 1 replace_colors 1
    spicetify backup apply
fi

echo "Done. Open a new terminal to see the prompt."
