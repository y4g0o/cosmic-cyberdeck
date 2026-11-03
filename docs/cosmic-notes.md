# COSMIC 1.11 notes (what the layout engine relies on)

Findings from building `montar.py` + `wl/cosmic.py` on Pop!_OS 24.04 with COSMIC 1.11 (Wayland).

## Works live (Wayland client, pywayland in `.venv`)
- **List** outputs, workspaces per output (with tiling state) and windows (app_id, title, output, workspace,
  exact geometry). COSMIC only sends toplevel data on its **next cycle**, so `Cosmic.atualizar()` waits briefly
  and does a roundtrip.
- **Toggle tiling** on a workspace: `zcosmic_workspace_handle_v2.set_tiling_state` + `ext_workspace_manager_v1.commit`.
- **Move a window** to a workspace + output: `zcosmic_toplevel_manager_v1.move_to_ext_workspace` (v4).
- **Activate** a workspace (`ext_workspace_handle_v1.activate`) and a window (`zcosmic_toplevel_manager_v1.activate` + `wl_seat`).
- **Close** a window cleanly: `zcosmic_toplevel_manager_v1.close`.
- **Tiling exceptions** (always-floating apps): `~/.config/cosmic/com.system76.CosmicSettings.WindowRules/v1/tiling_exception_custom`,
  a list of `(appid: "<regex>", titles: ["<regex>"])`, reloaded live.

## Only after the next login
- **Gaps** (`gaps` in the theme, `(outer, inner)`) are read when the compositor starts. Toggling
  `com.system76.CosmicTheme.Mode/v1/is_dark` false→true also makes it reload.

## Does not work
- An invisible panel to reserve space collapses to 1 px even with `size: Custom(200)`.
- `cosmic-term` has no split panes and cannot run a command from the CLI (only `-w DIR`).
- A 100% transparent window is not listed nor tiled.

## Adopted solutions
- **Art zones = ghost window** (`wl/fantasma.py`): undecorated GTK4 window with `rgba(0,0,0,0.01)` background,
  title `cyberdeck:<name>`, app_id `cyberdeck.fantasma`; it tiles like a normal slot and the poster shows through.
  Uses `Gtk.Window` + `GLib.MainLoop` (no `Gtk.Application`, which can hang on D-Bus in some sessions).
- **Terminal roles**: `env SHELL=/usr/bin/fish CYBERDECK_PAPEL=<role> cosmic-term`. fish reads the variable, sets
  the title `cyberdeck:<role>` and starts cava or the HUD.

## Tiling split rule (measured)
- A new window in a tiled workspace **splits the focused window in half along its longer side**; with nothing
  focused it splits the root. Only halves, no free ratios. A moved window does not get focus, so the layout
  engine activates the target before each insertion. To force the other direction it presses Super+O; to resize,
  it holds Super+R and taps arrows (12 px per tap).
- Shortcuts apply to the output under the pointer, so a virtual mouse (`/dev/uinput`) moves it there first. With
  outputs at different heights the pointer must also move vertically.
- Sometimes COSMIC ignores the whole virtual keyboard for one run: rotations are verified and the device is
  recreated before retrying.
- A newly opened window spawns attached to the focused one: wait until it is on screen and still, park it on
  another workspace, then insert it.

## Workspace used by the layout
- The **trailing empty workspace** of each output (COSMIC always keeps one); tiling is enabled there. Windows on
  other workspaces are never touched; re-running reuses the `cyberdeck:*` windows already open. COSMIC does not
  offer `create_workspace` (capability is 0).

## Pitfalls
- `pkill -f pattern` kills your own shell when its command line contains the pattern. The HUD uses
  `^\S*python3 \S*hud\.py --painel`.
- pywayland callbacks must return `None`; `WlRegistry` objects must stay referenced (otherwise "Cannot find
  display"); proxies of closed windows must stay referenced too; exit with `os._exit` to avoid a cffi crash.
- `cosmic-randr list` output changed in 1.11 (`Make`/`Model` lines between the name and `Position`); a real sample
  is in `tests/dados/`.
- Theme palette in `CosmicTheme.Dark/v1/palette` must be `(...)`; the Builder's `Dark((...))` breaks the whole
  theme, including the login screen. 1.11 also requires `list_button` (filled in from `/usr/share/cosmic`).
- cava 0.7.4 inside cosmic-term: hex colors do not work (cosmic-term ignores palette redefinition); use color names.
- Spicetify: `backup apply` refuses if already applied; `spicetify config KEY VALUE` writes instead of reading.

## Files favorites (cosmic-files)
`~/.config/cosmic/com.system76.CosmicFiles/v1/favorites` accepts `Named(path: "...", name: "// PROJECTS")`,
besides `Home`, `Downloads`, `Path("...")`.
