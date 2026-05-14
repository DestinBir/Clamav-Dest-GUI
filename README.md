# ClamAV Dest GUI

ClamAV Dest GUI is a branded Tkinter frontend for ClamAV scans and signature updates, maintained under Code, Growth Alive.

## Goals

- Keep the codebase split by responsibility.
- Make the project installable and Flatpak-friendly.
- Preserve the current desktop workflow while making future changes easier.
- Present a polished, brand-aligned desktop interface with the company logo.

## Layout

- `clamav_dest_gui/app.py` wires the application together.
- `clamav_dest_gui/ui/` contains the Tkinter presentation layer.
- `clamav_dest_gui/services/` contains the ClamAV command execution logic.
- `clamav_dest_gui/config.py` stores application state and scan results.
- `flatpak/` contains Flatpak packaging files.

## Company

- Company: Code, Growth Alive
- Founder: Destin Biringanine
- Location: Bukavu, Sud-Kivu, Democratic Republic of the Congo
- Website: https://codegrowthalive.com
- GitHub: https://github.com/DestinBir

## Run locally

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
python main.py
```

## Flatpak

The Flatpak manifest is in `flatpak/io.github.destinbir.clamavdestgui.yml`.
It includes desktop and metainfo files plus a packaging path for the bundled logo assets.