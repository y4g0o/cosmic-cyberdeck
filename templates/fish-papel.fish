# cyberdeck — papel de cada terminal aberto pelo comando `cyberdeck` (variável CYBERDECK_PAPEL)
# abas novas herdam a variável do terminal: só o 1º shell dele assume o papel (senão nasce outro HUD/cava)
if status is-interactive; and set -q CYBERDECK_PAPEL
    set -l terminal (ps -o ppid= -p $fish_pid | string trim)
    if test (count (pgrep -P $terminal -x fish)) -gt 1
        set -e CYBERDECK_PAPEL
    end
end
if status is-interactive; and set -q CYBERDECK_PAPEL
    function fish_title
        echo cyberdeck:$CYBERDECK_PAPEL
    end
    switch $CYBERDECK_PAPEL
        case cava
            printf '\e]0;cyberdeck:cava\a'   # título antes do exec (o fish sai de cena)
            exec cava
        case hud
            # Mata qualquer hud.py antigo antes de iniciar o novo
            pkill -f '^\S*python3 \S*hud\.py --painel' 2>/dev/null   # começa no python3 (com ou sem caminho): não casa com o shell que chamou
            set -l n (python3 "{{RAIZ}}/hud.py" --linhas)
            printf '\e[2J\e[%d;%dr\e[%d;1H' (math $n + 1) $LINES (math $n + 1)
            python3 "{{RAIZ}}/hud.py" --painel 3 &
            disown
    end
end
