# cyberdeck — comando `cyberdeck`: monta a base de janelas (ver {{RAIZ}}/README.md)
function cyberdeck --description "monta o layout do cyberdeck (cyberdeck --plano só mostra)"
    "{{RAIZ}}/.venv/bin/python" "{{RAIZ}}/montar.py" $argv
end

function nota --description "gerencia notas rápidas do HUD (nota 'texto' | nota -d N | nota --limpar)"
    python3 "{{RAIZ}}/hud.py" --gerenciar-nota $argv
end

function cmds --description "catálogo de comandos (cmds [filtro] | cmds add 'cmd' 'desc')"
    python3 "{{RAIZ}}/hud.py" --cmds $argv
end

function hud --description "recarrega o HUD Cockpit no terminal atual"
    pkill -f '^\S*python3 \S*hud\.py --painel' 2>/dev/null   # começa no python3 (com ou sem caminho): não casa com o shell que chamou
    set -gx CYBERDECK_PAPEL hud
    set -l n (python3 "{{RAIZ}}/hud.py" --linhas)
    printf '\e[2J\e[%d;%dr\e[%d;1H' (math $n + 1) $LINES (math $n + 1)
    python3 "{{RAIZ}}/hud.py" --painel 3 &
    disown
end
