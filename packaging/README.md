# Windows packaging

Genome Sentinel is currently a Python local server plus a browser UI. For a normal Windows user, the next distribution step is to bundle the Python runtime and application into a native installer.

Recommended release flow:

1. Build a standalone executable with PyInstaller.
2. Include `app/`, `pipeline/`, `data/`, and `bin/` as application resources.
3. Keep user-generated data outside the read-only bundled resources.
4. Produce a signed Windows installer (`.exe`).
5. The installer should create Start Menu/Desktop shortcuts and an uninstaller.
6. On launch, start the local server on loopback only and open the UI.

The repository should not commit generated installer binaries. CI/release automation should create them as release artifacts.
