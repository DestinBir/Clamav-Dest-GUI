# Contributing to Code, Growth Alive Security Tools

Thanks for helping improve the project.

## Workflow

1. Create a focused branch for each change.
2. Keep edits small and explain the user-facing impact in the pull request.
3. Run the Python validation steps before opening a PR.

## Expectations

- Preserve the modular layout under `clamav_dest_gui/`.
- Prefer service classes for command execution and UI classes for presentation.
- Keep the branding aligned with Code, Growth Alive.
- Update the Flatpak manifest and workflows when packaging-related files change.

## Validation

- `python3 -m compileall -q main.py clamav_dest_gui`
- `python3 -m clamav_dest_gui --help` is not expected; use the GUI entrypoint instead.
- For Flatpak work, validate the manifest and desktop metadata together.
