# Contributing · Contribuindo

🇺🇸 [English](#english) · 🇧🇷 [Português](#português)

---

## English

Thanks for helping! This theme changes real desktop settings, so the rules below are about keeping everything **testable offline** and **reversible**.

### Setup

```bash
git clone https://github.com/<you>/cosmic-cyberdeck.git && cd cosmic-cyberdeck
sudo apt install python3-pil python3-numpy python3-pytest fonts-noto-cjk fish
python3 -m pytest -q
```

Run the tests with a throwaway HOME so nothing touches your desktop:

```bash
env -u WAYLAND_DISPLAY HOME="$(mktemp -d)" python3 -m pytest -q
```

Tests marked `wayland` (`tests/test_cosmic_vivo.py`) need a live COSMIC session and `.venv` with pywayland; they are skipped otherwise. Tests that draw text are skipped (with a message) if a font is missing.

### Rules

- **Never apply to your real desktop while developing.** Use `python3 install.py --dry-run`, `python3 aplicar.py --seco` and `python3 gerar_poster.py --todas --destino /tmp/p`.
- Anything that writes outside the repo must go through `install.py` so it is backed up and listed in `install.py --dry-run`. New target? Add it to `ALVOS` (aplicar.py) or `PASTAS`/`EXTRAS`/`GERADAS` (install.py) and add a test.
- No hardcoded user paths: use `Path(__file__)`, `Path.home()`, `$HOME`, XDG variables, `{{RAIZ}}`/`{{HOME}}` in templates.
- "Suggest, don't quote": no franchise names or logos on screen. `poster/modulos.py` has `TEXTOS_PROIBIDOS` and tests enforce it.
- Images in `fotos/` must be your own or license-compatible, and show no identifiable real person.
- Fonts: SIL OFL (or similar) only, with the license file next to the font.
- Style: match the surrounding code (Portuguese identifiers are fine; English is welcome in new docs). Keep functions pure where possible so they can be tested without a compositor.
- Commits: small, imperative subject (`hud: show swap usage`). PRs: describe what changes on the desktop and how you tested it (preview images help).

### Good first issues

1. **Generate `layout.toml` from `cosmic-randr list`**: `layout.py` already parses outputs and positions (`saidas_conectadas`, `posicoes`); add a `--gerar-layout` that writes a two-slot tree per monitor. Test with `tests/dados/cosmic-randr-1.11.txt`.
2. **Palette validator**: a test that every `paletas/*.toml` has the same keys as `acid.toml` and that all values are `#RRGGBB`.
3. **`install.py --fonts`**: copy `fontes/` and `brave-ntp/fontes/` to `~/.local/share/fonts/cosmic-cyberdeck/` (backed up like everything else) and run `fc-cache`.
4. **Light palette**: add `paletas/paper.toml` and check contrast of `texto` on `fundo` (WCAG ratio ≥ 4.5) in a test.
5. **English messages**: translate the `print()` messages of `install.py` and `aplicar.py` (keep behavior; update tests that match text).
6. **Palette preview**: `python3 gerar_poster.py --todas --destino` already works offline; add a small script that renders a swatch sheet of a palette to `docs/previews/`.

---

## Português

Obrigado por ajudar! Este tema mexe em configurações reais do desktop, então as regras abaixo servem para manter tudo **testável offline** e **reversível**.

### Preparação

```bash
git clone https://github.com/<voce>/cosmic-cyberdeck.git && cd cosmic-cyberdeck
sudo apt install python3-pil python3-numpy python3-pytest fonts-noto-cjk fish
python3 -m pytest -q
```

Rode os testes com um HOME descartável para nada tocar no seu desktop:

```bash
env -u WAYLAND_DISPLAY HOME="$(mktemp -d)" python3 -m pytest -q
```

Os testes marcados `wayland` (`tests/test_cosmic_vivo.py`) precisam de uma sessão COSMIC ativa e do `.venv` com pywayland; fora disso são pulados. Os testes que desenham texto são pulados (com aviso) se faltar uma fonte.

### Regras

- **Nunca aplique no seu desktop real enquanto desenvolve.** Use `python3 install.py --dry-run`, `python3 aplicar.py --seco` e `python3 gerar_poster.py --todas --destino /tmp/p`.
- Tudo que escreve fora do repositório passa pelo `install.py`, para entrar no backup e aparecer no `install.py --dry-run`. Destino novo? Adicione em `ALVOS` (aplicar.py) ou `PASTAS`/`EXTRAS`/`GERADAS` (install.py) e escreva um teste.
- Nada de caminho fixo de usuário: use `Path(__file__)`, `Path.home()`, `$HOME`, variáveis XDG, `{{RAIZ}}`/`{{HOME}}` nos templates.
- "Sugere, não cita": nada de nomes de franquia ou logos na tela. O `poster/modulos.py` tem `TEXTOS_PROIBIDOS` e os testes conferem.
- Imagens em `fotos/` precisam ser suas ou de licença compatível, e sem pessoas reais identificáveis.
- Fontes: só SIL OFL (ou parecida), com a licença ao lado da fonte.
- Estilo: siga o código ao redor (identificadores em português são normais; inglês é bem-vindo em docs novas). Prefira funções puras para dar para testar sem compositor.
- Commits: pequenos, assunto no imperativo (`hud: mostra uso de swap`). PRs: descreva o que muda no desktop e como testou (prévias ajudam).

### Boas primeiras issues

1. **Gerar o `layout.toml` a partir do `cosmic-randr list`**: o `layout.py` já lê saídas e posições (`saidas_conectadas`, `posicoes`); crie um `--gerar-layout` que escreva uma árvore de dois slots por monitor. Teste com `tests/dados/cosmic-randr-1.11.txt`.
2. **Validador de paletas**: um teste de que toda `paletas/*.toml` tem as mesmas chaves da `acid.toml` e todos os valores são `#RRGGBB`.
3. **`install.py --fonts`**: copiar `fontes/` e `brave-ntp/fontes/` para `~/.local/share/fonts/cosmic-cyberdeck/` (com backup como o resto) e rodar `fc-cache`.
4. **Paleta clara**: adicionar `paletas/paper.toml` e conferir num teste o contraste de `texto` sobre `fundo` (razão WCAG ≥ 4,5).
5. **Mensagens em inglês**: traduzir os `print()` do `install.py` e do `aplicar.py` (mesmo comportamento; ajuste os testes que comparam texto).
6. **Prévia de paleta**: o `python3 gerar_poster.py --todas --destino` já funciona offline; crie um script pequeno que gere uma cartela de cores da paleta em `docs/previews/`.
