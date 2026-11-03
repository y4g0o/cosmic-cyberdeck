<!-- gerado de templates/newtab.html.tpl por aplicar.py (assinatura em config.toml) -->
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>cyberdeck // new tab</title>
<link rel="stylesheet" href="ntp.css">
</head>
<body>
<div class="fundo"></div>
<main>
  <header>
    <span class="tag">// NODE 07 :: 接続中</span>
    <h1 id="hora">--:--</h1>
    <p id="data" class="sub">—</p>
  </header>
  <form action="https://search.brave.com/search" method="get" class="busca">
    <span class="prompt">⟩⟩</span>
    <input name="q" autofocus autocomplete="off" placeholder="search_" aria-label="Search">
  </form>
  <nav class="atalhos" id="atalhos"></nav>
  <form id="editor" class="editor" hidden>
    <input id="ed-nome" placeholder="NAME" maxlength="16" required>
    <input id="ed-url" placeholder="https://..." required>
    <button type="submit">SAVE</button>
    <button type="button" id="ed-cancelar">CANCEL</button>
  </form>
  <button id="editar" class="editar">EDIT</button>
  <footer><span>{{ASSINATURA}} // OPERADOR</span><span>SIGNAL ACQUIRED</span></footer>
</main>
<script src="ntp.js"></script>
</body>
</html>
