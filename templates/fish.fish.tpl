# cyberdeck — remover este arquivo desfaz as cores do terminal
if status is-interactive
    command -q starship; and starship init fish | source
    set -g fish_color_command {{hex:accent}}
    set -g fish_color_param {{hex:foco}}
    set -g fish_color_error {{hex:alerta}}
    set -g fish_color_quote {{hex:ansi_5}}
    set -g fish_color_autosuggestion {{hex:fraco}}
    set -g fish_color_operator {{hex:ansi_2}}
    alias netrun 'btop'
    abbr --add cyberdeck-icones 'python3 "{{RAIZ}}/gerar_icones.py"'
    # aplicar.py muda a variável universal cyberdeck_paleta: todo fish aberto relê este arquivo com as cores novas
    set -g __cyberdeck_cores (status filename)
    function __cyberdeck_recarregar --on-variable cyberdeck_paleta
        source $__cyberdeck_cores
    end
end
