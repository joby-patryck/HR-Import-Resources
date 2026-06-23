# HR Import Resources

Interactive CLI utility for normalizing and splitting HR export CSV files (Users and Job Assignments) before they are imported into downstream systems (the Lift LMS). Files are normalized (validated, lowercased, suspended accounts filtered) and tenant-specific records are extracted into separate output files with an auto-enrollment column added.

## Download & run (no setup)

Pre-built desktop versions of the GUI ([App.py](App.py)) are published on the [Releases](../../releases) page — no Python, `pip`, or setup required.

1. Download the file for your OS from the latest release:
   - **Windows** — `HR-Import-Windows.zip` → unzip → run `HR Import.exe`
   - **macOS** — `HR-Import-macOS.zip` → unzip → run `HR Import.app`
2. **Place your `dont_suspend.csv` next to the app** (same folder as `HR Import.exe`, or alongside `HR Import.app`). It is not bundled — without it the app still runs, but the retain-list filter is skipped (you'll see a warning in the log). See step 4 of **Setup** for the file format.

> **First launch — unsigned app warnings.** These builds are not code-signed, so the OS will warn the first time:
> - **Windows:** SmartScreen → click **More info → Run anyway**.
> - **macOS:** right-click the app → **Open** → **Open** (don't double-click the first time).

The `tenants.json` config *is* bundled into the app; to change tenants you rebuild (see **Building the desktop app**).

## Requirements

- [Python 3.11+](https://www.python.org/downloads/) — install from **python.org** or Homebrew. On macOS, do **not** use the system `/usr/bin/python3` (Apple Command Line Tools): its bundled Tcl/Tk is broken and the GUI aborts with `macOS 15 (1507) or later required`.
- [pandas](https://pandas.pydata.org/) — the only `pip`-installable dependency (installed via `requirements.txt` below).
- **tkinter** — required only by the GUI ([App.py](App.py)). It ships with most Python builds but is **not** on PyPI, so it cannot be installed with `pip`. If `python -c "import tkinter"` fails, install it as an OS package:

  | Platform | Command |
  |---|---|
  | macOS (Homebrew) | `brew install python-tk` |
  | Debian / Ubuntu | `sudo apt install python3-tk` |
  | Fedora | `sudo dnf install python3-tkinter` |
  | Windows | included with the [python.org installer](https://www.python.org/downloads/) |

Everything else the program uses (`json`, `os`, `re`, `sys`, `shutil`, `pathlib`) is part of the Python standard library.

## Setup

1. Clone or download this repository.

2. Create and activate a virtual environment, then install the pip dependencies from [requirements.txt](requirements.txt). Using a venv pins the project to a known-good interpreter (important on macOS — see **Requirements**):

   **macOS / Linux:**

   ```bash
   python3 -m venv .venv          # on macOS use python3.13 if python3 is Apple's broken build
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

   **Windows (PowerShell):**

   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

   This installs `pandas`. Inside the activated venv, `python` and `pip` both point to the correct interpreter. If you plan to run the GUI, also make sure `tkinter` is available (see **Requirements** above). The `.venv/` folder is git-ignored.

3. Verify your Python can run the GUI toolkit:

   ```bash
   python -c "import tkinter; tkinter.Tk()"
   ```

   A small empty window should appear (close it). If it errors instead, fix `tkinter` / your Python install before continuing.

4. Create a `dont_suspend.csv` file in the project directory (it is git-ignored). It must contain an `email` column listing the IDs (matched against `idnumber` / `useridnumber`) that should always be filtered out:

   ```csv
   email
   first.last1@email.com
   first.last2@email.com
   ```

## Usage

Run the interactive CLI from the project directory:

```powershell
# Run with no tenant splitting
python Main.py

# Run with one or more tenant IDs (case-insensitive, must exist in tenants.json)
python Main.py jbg
python Main.py jbg jaa
```

After launch, paste a CSV path at the prompt (surrounding quotes and backslashes are stripped automatically). The CLI keeps prompting for files until you enter `q`, `quit`, or `exit`.

Other arguments:

- `-h` / `--help` — print usage and exit.

> **Note:** The filename **must** contain either `Users` or `Job Assignments` (case-insensitive). That substring is what routes processing.

## What it does

Every processed file is backed up first, then transformed in place.

- **`Job Assignments` files** — drops rows with a missing `useridnumber`, fills missing `Manager email` values with `#N/A`, drops suspended users (`suspended == 1`), and lowercases `Manager email` and `useridnumber`.
- **`Users` files** — drops rows with a missing `idnumber`, splits out tenant-specific rows (see below), filters by suspension state (see *Terminated files* below), lowercases `idnumber` and `email`, and clears the `tenantmember` column on the remaining (non-tenant) rows.
- Both paths drop any account whose ID appears in `dont_suspend.csv` (matched against `idnumber` / `useridnumber`).

### Terminated files

For `Users` files whose name contains `terminated` (case-insensitive), the suspension handling is inverted: only suspended rows (`suspended == 1`) are kept, the existing `deleted` column is dropped, and `suspended` is renamed to `deleted`. Non-terminated `Users` files instead keep only active rows (`suspended == 0`).

### Tenant splitting

Tenant definitions live in [tenants.json](tenants.json) (currently `jbg` — Joby Aviation Germany, and `jaa` — Joby Aviation Academy). For each tenant ID passed on the command line, rows whose `business unit description` matches the tenant's configured value (case-insensitive, whitespace-trimmed) are written to a sibling file `<original> <tenant_id>.csv` with an added `tenantmember` column (set to the tenant ID) used downstream for auto-enrollment. Those rows are removed from the main output, and the new tenant file is then run through the same normalization (with no further tenant splitting).

> **Warning:** The original CSV is overwritten in place when processing completes. Before each file is processed, a backup of the original is copied to an `original_files/` subfolder (alongside the input file) prefixed with `Original `.

## Building the desktop app

The download-and-run builds above are produced by [PyInstaller](https://pyinstaller.org/) from [HRImport.spec](HRImport.spec). PyInstaller **cannot cross-compile** — each OS's artifact must be built on that OS.

**Automated (recommended).** The [build workflow](.github/workflows/build.yml) builds both the Windows `.exe` and macOS `.app` on GitHub's runners. Push a version tag and the zipped artifacts are attached to the matching Release automatically:

```bash
git tag v1.0.0
git push origin v1.0.0
```

(You can also trigger it manually from the Actions tab via **Run workflow** to get artifacts without publishing a release.)

**Local build.** From an activated venv with dependencies installed (see **Setup**):

```bash
pip install pyinstaller
pyinstaller HRImport.spec        # output in dist/  (HR Import.exe / HR Import.app)
```

The build bundles `tenants.json`; `dont_suspend.csv` is intentionally left external and user-editable (resolved next to the app at runtime — see [resources.py](resources.py)).

## Project layout

| File | Purpose |
|---|---|
| [Main.py](Main.py) | Entry point — validates tenant arguments, backs up originals, and runs the read → process loop. |
| [HRImport.py](HRImport.py) | `HRImport.run()` — dispatches and performs processing based on the filename. |
| [Tenants.py](Tenants.py) | `load_tenants()` — reads tenant definitions from `tenants.json`. |
| [resources.py](resources.py) | Resolves data-file paths in both dev and packaged (PyInstaller) builds. |
| [HRImport.spec](HRImport.spec) | PyInstaller build recipe for the desktop app. |
| [.github/workflows/build.yml](.github/workflows/build.yml) | CI that builds the Windows/macOS apps and attaches them to Releases. |
| [tenants.json](tenants.json) | Tenant ID → business-unit configuration. |
| `dont_suspend.csv` | Local (git-ignored) list of IDs to always retain. Required at runtime. |
| [not_in_both.py](not_in_both.py) | Standalone helper (not wired into `Main.py`). **LEGACY** |
| [requirements.txt](requirements.txt) | Python dependencies. |
