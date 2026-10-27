# LET'S GO FOR VROUVES / ΠΑΜΕ ΓΙΑ ΒΡΟΥΒΕΣ (PC)

A cute top-down tower defence for Windows, Linux and macOS, made with Godot 4.7. It is a
port of the Amstrad CPC game in `../VrouvesCPC`: the same seven stages, waves, defenders,
invaders and rules, with new cartoon graphics rendered in Blender.

Armed with EU Directive 8647/2026, Frankenstein & Moreau Co. send bio-drones, compliance
guards and weed-destroying tanks to wipe out the wild, "copyrighted" *vrouves* of Crete.
The villagers of Zoniana defend their sacks of bitter greens, helped by the defected drone
Psssst.

## Playing

Open the folder in Godot 4.7 and press F5, or run an exported build. The player's manual
is in [English](manual/Manual-EN.md) and [Greek](manual/Manual-GR.md);
`tools/make_manual_pdf.py` prints both to PDF in `build/manual/` (it needs the `markdown`
package and Microsoft Edge on the Windows side of WSL).

| Mouse / key | Action |
| --- | --- |
| Point at a tile, left click / SPACE | Build the chosen defender |
| Right click / S | Sell (half price back) |
| 1 – 6, or click a card | Choose a defender |
| Arrows / Q A O P | Move the cursor |
| N | Call the next wave now (half the seconds left are paid as a bonus) |
| F | Game speed x1 / x2 / x3 |
| H | Pause; ESC pauses, ESC again quits to the title |
| L | English / Ελληνικά |
| M | Music on / off |
| F11, Alt+Enter | Full screen |

The rules are the CPC ones; `docs/cpc_mechanics.md` has every number (25 logic ticks a
second, path steps, ranges, armour, neighbour bonuses, score, lives).

## Making it

* `tools/export_stages.py` copies the stage data of the CPC version (maps, ground and air
  paths, sacks, waves) into `data/stages.json`.
* `tools/make_audio.py` (numpy) makes `art/audio/`: the CPC tune on a lyra-like lead and a
  plucked bass, and the CPC's AY sound effects.
* `tools/blender/` builds the art in Blender (run through the Blender MCP or Blender's
  Python console, with that folder on `sys.path`):
  * `blender_toon.py` – the flat two-tone materials, outlines and villagers of the CPC
    version's Blender scenes;
  * `models.py` – the cast and props, and `Rig`, an orthographic camera tilted 62° so every
    map cell is a 128 × 128 square;
  * `render_sprites.py` – `art/sprites/` (defenders, invaders in four directions and two
    frames, sacks, shots, effects);
  * `render_stages.py` + `buildings.py` – `art/stages/stageN.png`, each stage's map with its
    building (kafenio, church, town hall, bakery, school, pitch, cemetery chapel);
  * `title_blender.py` and `ending_blender.py` – `art/title.png` and `art/ending.png`.

  The stage pictures are rendered at 2560 × 1792 and scaled to 1920 × 1344.
* `tools/run_windowed.sh SECS [args]` runs the game from WSL in a window for SECS seconds,
  saving screenshots to `scratch/`. Game arguments (after `--`): `--stage N` starts at a
  stage, `--bot` lets it play itself (`--botspeed N`), `--perf` prints frame timings,
  `--shots DIR` saves a screenshot every 3 s, `--exit SECS` quits, `--lang en|gr` sets the
  language for that run.

## Exporting

`export_presets.cfg` has Windows, Linux and macOS presets (output in `build/`). They need
the Godot 4.7.2 export templates (Editor → Manage Export Templates), then e.g.

```
godot --headless --export-release "Windows" build/windows/LetsGoForVrouves.exe
```

The macOS build is unsigned; on a Mac, right click → Open the first time.

The icon (Psssst over a sack of vrouves) is rendered by `tools/blender/icon_blender.py`
to `art/icon_1024.png`; `tools/make_icons.py` makes `art/icon.ico` (put into the Windows
.exe by the export), `art/icon.png` and the setup's icons.

## Setup

`installer/` is the setup program, in C# with Avalonia 11 on .NET 10: one self-contained
file per platform with the game inside it. It installs for the current user, without
administrator rights, offers desktop and menu shortcuts, and leaves an uninstaller next to
the game (in Settings → Apps on Windows), in English or Greek.

| | Installs to | Shortcuts |
| --- | --- | --- |
| Windows | `%LOCALAPPDATA%\Programs\LetsGoForVrouves` | Start menu, desktop |
| Linux | `~/.local/share/LetsGoForVrouves` | applications menu, desktop |
| macOS | `~/Applications/Let's Go For Vrouves.app` | alias on the desktop |

After exporting the game, `installer/build.sh` writes `build/setup/`:
`VrouvesSetup-windows-x64.exe`, `VrouvesSetup-linux-x64` and
`VrouvesSetup-macos-{x64,arm64}.zip` (an unsigned .app). The setup also takes
`--quiet` (install or uninstall without questions), `--dir DIR`, `--no-shortcuts` and
`--uninstall`.

Fonts: Noto Sans (SIL Open Font License, `art/fonts/LICENSE-noto.txt`).
