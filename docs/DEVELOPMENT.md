# Development Guide

## Prerequisites

- Python with support for the versions of Pygame CE and NumPy selected by pip.
- A desktop environment with a display for interactive use.

No Python version range is declared in the repository. The dependency installation and headless render smoke test were verified in the current Windows environment with Python 3.14.7.

## Install

From the repository root in PowerShell:

```powershell
python -m pip install -r .\starry_night\starry_night\requirements.txt
```

Or, from the application source directory:

```powershell
Set-Location .\starry_night\starry_night
python -m pip install -r requirements.txt
```

## Run

From the repository root:

```powershell
python .\starry_night\starry_night\main.py
```

From the application source directory:

```powershell
python main.py
```

The application uses Pygame CE, whose installed distribution name is `pygame-ce` and whose Python import name remains `pygame`.

## Tests and checks

Run the unit tests from the repository root:

```powershell
python -m unittest discover -s .\starry_night\starry_night\tests -t .\starry_night\starry_night
```

Run a headless rendering smoke test:

```powershell
$env:SDL_VIDEODRIVER = "dummy"
python .\starry_night\starry_night\main.py --save-frame smoke-test.png --frames 1
```

The smoke test writes `smoke-test.png` in the current directory. Use `--bench --frames 300` to measure frame cost on the current machine; benchmark results are machine- and environment-specific and should not be treated as a project-wide performance guarantee.

There is no configured formatter, linter, static type checker, packaging build, or continuous-integration workflow. Do not report those checks as passing unless they are configured and run.

## Implementation notes

- `starry.config` is the source of the logical canvas size, target frame rate, and default random seed.
- The landscape and sky are pre-rendered during scene initialization; interactive frames mostly update and compose surfaces.
- Brush sprites are cached by color, size, variant, and rotation index. Avoid adding unbounded cache keys to long-running animation paths.
- Use the scene's seeded NumPy generator when adding procedural scene randomness.
- Keep any new generated outputs out of source control unless they are intentional project assets.

## Repository and licensing notes

Python bytecode, caches, virtual environments, build output, and common local test artifacts are excluded by the repository `.gitignore`. Runtime frame exports are written to the path chosen by the user and are not ignored by a broad image rule, so intentional project assets such as `preview.png` remain trackable.

No project `LICENSE` file or verified copyright-holder information is present. Do not add a license or claim that the source is open source until the rights holder and intended terms are established. Third-party dependencies retain their own licenses.
