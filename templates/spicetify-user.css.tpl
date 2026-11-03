/* cyberdeck — gerado de paletas/ */
:root {
  --nc-yellow: {{accent}}; --nc-cyan: {{foco}}; --nc-red: {{alerta}};
  --nc-cut: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 12px 100%, 0 calc(100% - 12px));
}
body, .encore-text, button, input { font-family: "Rajdhani", "Share Tech Mono", sans-serif !important; letter-spacing: .02em; }
h1, h2, .main-entityHeader-title { font-family: "Orbitron", "Rajdhani", sans-serif !important; text-transform: uppercase; }

/* cantos chanfrados em vez de arredondados */
.main-card-card, .main-trackList-trackListRow, img, .main-image-image,
.Root__nav-bar, .Root__main-view, .Root__right-sidebar, .main-nowPlayingBar-nowPlayingBar {
  border-radius: 0 !important;
}
.main-card-card { border-left: 2px solid var(--nc-yellow); }
.main-card-card:hover { background: {{sup_b}} !important; border-left-color: var(--nc-cyan); }

/* botão play amarelo com chanfro */
.main-playButton-PlayButton button, .main-playButton-PlayButton > span,
button[data-testid="play-button"] > span { border-radius: 0 !important; clip-path: var(--nc-cut); background-color: var(--nc-yellow) !important; color: {{fundo}} !important; }

/* barras de progresso/volume */
.progress-bar { --fg-color: var(--nc-cyan) !important; --bg-color: {{roxo_profundo}} !important; }
.progress-bar__slider { border-radius: 0 !important; background: var(--nc-yellow) !important; }

/* linha selecionada/tocando */
.main-trackList-trackListRow:hover { background: linear-gradient(90deg, rgba({{rgb:accent}},.12), transparent) !important; }
.main-trackList-playing .main-trackList-rowTitle, .main-trackList-active { color: var(--nc-cyan) !important; }

::-webkit-scrollbar-thumb { background: var(--nc-yellow) !important; border-radius: 0 !important; }
