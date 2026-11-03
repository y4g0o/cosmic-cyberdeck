# cyberdeck — gerado de paletas/
format = """
[](fg:{{accent}})$os$username[](fg:{{accent}} bg:{{foco}})$directory[](fg:{{foco}} bg:{{alerta}})$git_branch$git_status[](fg:{{alerta}} bg:{{roxo_profundo}})$python$nodejs$rust$cmd_duration[](fg:{{roxo_profundo}})
[⟩⟩ ](bold {{accent}})"""
right_format = "$time"
add_newline = true

[os]
disabled = false
style = "bg:{{accent}} fg:{{fundo}}"
format = "[ $symbol]($style)"
[os.symbols]
Pop = " "
Ubuntu = " "

[username]
show_always = true
style_user = "bg:{{accent}} fg:{{fundo}} bold"
format = "[$user ]($style)"

[directory]
style = "bg:{{foco}} fg:{{fundo}} bold"
format = "[ $path ]($style)"
truncation_length = 3
truncation_symbol = "…/"

[git_branch]
symbol = ""
style = "bg:{{alerta}} fg:{{quase_branco}}"
format = "[ $symbol $branch ]($style)"

[git_status]
style = "bg:{{alerta}} fg:{{quase_branco}} bold"
format = "[$all_status$ahead_behind ]($style)"

[python]
style = "bg:{{roxo_profundo}} fg:{{accent}}"
format = "[ $symbol$version ]($style)"
[nodejs]
style = "bg:{{roxo_profundo}} fg:{{ansi_2}}"
format = "[ $symbol$version ]($style)"
[rust]
style = "bg:{{roxo_profundo}} fg:{{laranja}}"
format = "[ $symbol$version ]($style)"

[cmd_duration]
min_time = 2000
style = "bg:{{roxo_profundo}} fg:{{ansi_5}}"
format = "[ 󱑂 $duration ]($style)"

[time]
disabled = false
time_format = "%H:%M"
style = "fg:{{foco}}"
format = "[ cyberdeck//$time ]($style)"
