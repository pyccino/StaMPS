# Installing StaMPS on Windows

This guide covers the native Windows install flow for the StaMPS Windows
port (SNAP preprocessor path). If you are installing on Linux or macOS,
see the legacy `INSTALL` file; the Linux/GAMMA/DORIS/ISCE preprocessor
paths are not supported on Windows (see Section 9).

If you are running inside WSL, use the Linux install flow inside the WSL
distribution — do **not** run `install-windows.ps1` from WSL. The
installer detects WSL via `$env:WSL_DISTRO_NAME` / `/proc/version` and
aborts with exit code 2.

---

## 1. Prerequisites

| Requirement | Version | Notes |
| --- | --- | --- |
| Windows | 10 21H2+ or Windows 11 (x64) | Older builds lack long-path and UTF-8 console support. |
| MATLAB | R2023a or newer (R2025a tested) | See the `MATLAB_EXE` workaround below if `matlab.exe` is not on `PATH`. |
| Python | 3.11+ from [python.org](https://www.python.org/downloads/windows/) | **Do not** use the Microsoft Store "python.exe" stub — it proxies to the Store and breaks subprocess spawning. |
| SNAP | 9.x from [ESA STEP](https://step.esa.int/main/download/snap-download/) | Required by the PHASE preprocessor path. |
| Git | 2.40+ | For cloning the fork; also used by `install-windows.ps1` to auto-detect the repo slug. |
| PowerShell | 5.1 (built in) or PowerShell 7+ | Both are supported. |

### Verify each prerequisite

Open a new PowerShell window and run:

```powershell
py -3 --version                      # expect 3.11.x or newer
python -c "import sys; print(sys.executable)"   # expect a path under C:\Python311 or similar, NOT ...\WindowsApps\...
matlab.exe -batch "disp(version)"    # expect 9.14+ (R2023a == 9.14)
git --version
```

If `python` prints a `WindowsApps` path and opens the Microsoft Store:

1. Open **Settings → Apps → Advanced app settings → App execution aliases**.
2. Toggle **App Installer — python.exe** and **python3.exe** off.
3. Install CPython from python.org and tick *Add Python to PATH*.

### MATLAB not on PATH

If MATLAB is installed but `matlab.exe` is not on `PATH`, set
`MATLAB_EXE` to the absolute path before running any StaMPS command:

```powershell
$env:MATLAB_EXE = "C:\Program Files\MATLAB\R2025a\bin\matlab.exe"
```

Persist it across sessions with **System Properties → Environment
Variables** (or `setx MATLAB_EXE "..."` from an admin shell). All
StaMPS helpers (`sp_system`, `sp_runcmd`, the `.bat` shims) honour this
variable.

---

## 2. PowerShell execution policy

By default, Windows PowerShell blocks unsigned `.ps1` files. The v1.0.0
StaMPS release is unsigned (see Section 5); set an execution policy for
your user account once:

```powershell
# One-time per user account:
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force
```

`RemoteSigned` allows local scripts to run while still requiring
downloaded scripts to be signed or unblocked.

If you downloaded the release zip and Windows tagged its contents as
"from the Internet" (the NTFS `Zone.Identifier` stream), unblock every
`.ps1` after extraction:

```powershell
Get-ChildItem -Recurse *.ps1 | Unblock-File
```

---

## 3. Fast path — prebuilt binaries

Recommended for all non-developer installs. Requires `gh` CLI for
Sigstore attestation verification (strongly recommended; see Section
10).

```powershell
# In an empty directory, e.g. C:\StaMPS:
git clone https://github.com/pyccino/StaMPS.git C:\StaMPS
cd C:\StaMPS
git checkout windows-port/main

# Run the installer — downloads the latest release zip, verifies
# SHA256 + Sigstore attestation, extracts into the current directory,
# and builds Triangle from vendored source.
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-windows.ps1
```

The installer:

1. Aborts if it detects WSL.
2. Probes `HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem\LongPathsEnabled` and warns if disabled (see Section 6).
3. Warns if the install path is inside OneDrive or contains non-ASCII characters.
4. Fetches `stamps-windows-x64-msvc.zip` from the latest release of the detected repo (auto-detected from `remote.fork` or `remote.origin`; override with `-Repo pyccino/StaMPS`).
5. Verifies `SHA256SUMS-msvc` against the downloaded zip.
6. Verifies the Sigstore attestation via `gh attestation verify` (retries 3× on transient failure; override with `-IAcceptUnverifiedRisk` only if you accept the risk).
7. Unpacks into `-InstallDir` (defaults to `$PSScriptRoot`).
8. Builds Triangle from the vendored source under `external\triangle\`.

After install, dot-source the config in every new PowerShell session:

```powershell
. C:\StaMPS\StaMPS_CONFIG.ps1
```

Switches:

| Flag | Effect |
| --- | --- |
| `-Repo pyccino/StaMPS` | Override the auto-detected slug. |
| `-Version v1.0.0` | Pin to a specific tag (default: `latest`). |
| `-InstallDir D:\tools\StaMPS` | Install somewhere other than the script directory. |
| `-SkipAttestation` | Skip Sigstore verification (SHA256 still enforced). |
| `-IAcceptUnverifiedRisk` | Proceed if attestation verification fails 3×. |
| `-DryRun` | Run all probes without downloading or unpacking. |

---

## 4. Build from source (MSVC)

Only needed if you want to modify StaMPS or cannot use the release zip.
Requires Visual Studio 2022 (Community is fine) with the **Desktop
development with C++** workload and CMake 3.20+.

```powershell
git clone --recurse-submodules https://github.com/pyccino/StaMPS.git
cd StaMPS
git checkout windows-port/main

# Configure + build the StaMPS C++ binaries:
cmake -S src -B build -G "Visual Studio 17 2022" -A x64
cmake --build build --config Release

# Build the vendored Triangle (Shewchuk) source:
cmake -S external/triangle -B build-triangle
cmake --build build-triangle --config Release
cmake --install build-triangle --prefix external/triangle

# Build snaphu from the vendored CMake wrapper:
cmake -S external/snaphu -B build-snaphu
cmake --build build-snaphu --config Release
```

Binaries land in `bin\`. Add that directory to `PATH` (handled
automatically when you dot-source `StaMPS_CONFIG.ps1`).

### MinGW alternative (unofficial)

The release workflow produces a `stamps-windows-x64-mingw.zip` as a
secondary artifact. Build locally with MSYS2:

```bash
# From an MSYS2 MINGW64 shell:
pacman -S --needed mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake mingw-w64-x86_64-ninja
cmake -S src -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

MinGW builds are run against the byte-identity golden-file harness
on CI but receive less manual testing than MSVC.

---

## 5. SmartScreen first-run workflow

v1.0.0 is **unsigned**: Windows SmartScreen will show *"Windows
protected your PC"* the first time you launch any StaMPS `.exe` or run
`install-windows.ps1`. v1.0.1 and later will be signed via SignPath's
OSS program (tracked in `docs/SIGNPATH_STATUS.md`).

### Click-path for v1.0.0

1. In the SmartScreen dialog click **More info** (the link is small and appears below the "Don't run" button).
2. A **Run anyway** button appears — click it.
3. The prompt is once-per-binary-per-user; you will not see it again for the same file.

Screenshots of the exact dialog are pending the v1.0.0 release smoke
test and will be added here.

### Corporate antivirus / Microsoft Defender

Enterprise Defender policies sometimes quarantine unsigned binaries
even after SmartScreen approval. Add the install directory to the
exclusion list (requires admin PowerShell):

```powershell
Add-MpPreference -ExclusionPath "C:\StaMPS\bin"
```

Third-party AV (CrowdStrike, SentinelOne, McAfee) needs a similar
exclusion — consult your corporate IT.

---

## 6. Windows long paths (MAX_PATH = 260)

StaMPS creates deep `PATCH_N/` directories during processing; a single
absolute path can exceed the legacy 260-character limit, producing
cryptic `CreateFile` / `fopen` failures. Two mitigations (pick one):

### Option A — enable long paths globally (preferred; needs admin)

```powershell
# Run once from an elevated PowerShell:
Set-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' `
                 -Name LongPathsEnabled -Value 1
```

A reboot is **not** required, but already-running processes must be
restarted to pick up the new flag. Python 3.6+ sets the per-process
long-path manifest bit automatically (PEP 519-era change), so Python
parts of StaMPS already honour the registry flag once enabled.

### Option B — install under a short root (no admin needed)

Place StaMPS at `C:\StaMPS\` (or any drive root). **Avoid**:

- `C:\Users\<you>\OneDrive\Documents\...` (OneDrive + deep Documents).
- Network shares via UNC with long server names.
- Project directories under `C:\Users\<you>\source\repos\...`.

`install-windows.ps1` emits a warning when both of these conditions
are true, but it will still proceed.

---

## 7. Locale considerations

The Python port of StaMPS is **locale-invariant by design**: every
numeric parse goes through explicit `float()` / `np.loadtxt` with
`C`-locale-equivalent parsing, so decimal-comma locales (German,
Italian, French) do not corrupt patch tables.

The C++ binaries under `bin\` pin `LC_NUMERIC=C` at startup (see the
`setlocale` calls in `selpsc_patch.cpp`, `selsbc_patch.cpp`,
`ps_load_initial_gamma.cpp`, etc.); no manual configuration is
needed.

### MATLAB

On Windows, MATLAB R2020a+ ships a non-UTF-8 default encoding. Add
to your MATLAB `startup.m`:

```matlab
slCharacterEncoding('UTF-8');
```

This prevents mojibake when StaMPS reads SNAP-generated metadata that
contains accented characters (e.g. German station names in TSX/TDX
auxiliary files).

### Terminal

Use **Windows Terminal** (Microsoft Store) rather than legacy
`conhost.exe`. Windows Terminal supports UTF-8 output natively;
`conhost` handles UTF-8 only if you first run `chcp 65001`.

---

## 8. OneDrive caveat

Files inside a OneDrive-synced folder can be silently locked mid-run
while OneDrive uploads them, producing intermittent
`PermissionError: [WinError 32]` from Python or
`fopen: Permission denied` from the C++ binaries.

Mitigations, in order of preference:

1. **Install StaMPS outside OneDrive.** `C:\StaMPS\` is recommended.
2. **Pause OneDrive** before long runs (taskbar icon → *Pause syncing*).
3. **Exclude the StaMPS data directory** via OneDrive settings →
   *Account → Choose folders*.

The Python helpers in `matlab_compat/_shell.py` already retry
file-I/O operations 3× with 100 ms backoff to paper over the
narrowest sync races, but sustained contention will still fail.

---

## 9. Known limitations on Windows

### Not ported

| Component | Status | Workaround |
| --- | --- | --- |
| `dismph` (X11/Motif display tool) | Linux-only, no Windows port planned. | Use the SNAP GUI or MATLAB `imagesc(abs(ph))` / `imagesc(angle(ph))`. |
| `mt_prep_gamma`, `mt_prep_doris`, `mt_prep_isce` | Linux-only. | Preprocess on Linux, copy the output tree to Windows, then run `mt_prep_snap` equivalents. Only the SNAP path is supported natively. |
| Legacy `make_*` shell scripts | Linux/csh-only. | Use the PowerShell and Python equivalents under `python/` and `matlab_compat/`. |
| TRAIN atmospheric-correction module | Linux-only, no Windows port planned. | Run TRAIN on a Linux box or inside WSL. |
| `csh` / `tcsh` wrappers | Not available. | PowerShell `.ps1` + `.bat` shims replace them. |

### Supported path

The SNAP preprocessor path (`mt_prep_snap`, the `stamps.m` pipeline,
`stamps_mc_plot`, PS + SB selection, unwrapping via `snaphu`, MATLAB
post-processing) is fully supported natively on Windows. Every C++
binary in `bin\` is covered by the cross-platform golden-file test
harness.

---

## 10. Verifying release authenticity (Sigstore attestation)

Every release zip ships with a Sigstore attestation bundle published
to GitHub's attestations API. Verify it with the GitHub CLI:

```powershell
# Install gh CLI if needed: https://cli.github.com
gh attestation verify stamps-windows-x64-msvc.zip --owner pyccino
```

Successful output ends with `Verification succeeded!`. Failure means
either the artifact has been tampered with **or** GitHub's
attestations API is transiently unreachable — retry 2–3 times before
concluding the artifact is bad. `install-windows.ps1` performs this
verification automatically with retry + opt-out semantics; see the
`-SkipAttestation` and `-IAcceptUnverifiedRisk` flags in Section 3.

You can also verify the CycloneDX SBOM published with each release
(`sbom.cdx.json`) against the same attestation.

---

## 11. Troubleshooting

### `matlab.exe: command not found`

MATLAB is installed but `bin\` is not on `PATH`. Set `MATLAB_EXE`:

```powershell
$env:MATLAB_EXE = "C:\Program Files\MATLAB\R2025a\bin\matlab.exe"
```

### Running `python` opens the Microsoft Store

Remove the Store alias (Settings → Apps → Advanced app settings → App
execution aliases → disable **python.exe** and **python3.exe**) and
install CPython from python.org with the *Add to PATH* option ticked.

### `install-windows.ps1` aborts with "Running inside WSL"

Expected. `install-windows.ps1` is for native Windows only. Inside
WSL, use the Linux install flow (`INSTALL` in the repo root). Exit
code 2.

### `install-windows.ps1` prints "Sigstore attestation verification failed 3 times"

Either the zip has been tampered with, or GitHub's attestations API
is down. First, retry after a few minutes. If it still fails, check
https://www.githubstatus.com/ for an active incident. Only as a last
resort, re-run with `-IAcceptUnverifiedRisk` — but only on networks
you trust.

### `CreateFile ... The system cannot find the path specified` deep in a `PATCH_N/` directory

Long-path support is disabled. See Section 6.

### Intermittent `PermissionError [WinError 32]` during a long run

Something is locking the file — most often OneDrive or Windows
Defender real-time scanning. See Sections 5 and 8.

### `UnicodeDecodeError` when reading SNAP metadata

Your MATLAB `startup.m` is missing `slCharacterEncoding('UTF-8')`
and SNAP is producing UTF-8 output that MATLAB is interpreting as
Windows-1252. Fix per Section 7.

### PowerShell refuses to run `install-windows.ps1` ("execution of scripts is disabled")

Your `ExecutionPolicy` is `Restricted` (the factory default on some
managed Windows images). Run the one-time command in Section 2, or
pass `-ExecutionPolicy Bypass` once:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-windows.ps1
```

---

## Where to get help

- Open an issue at https://github.com/pyccino/StaMPS/issues.
- Include: Windows build (`winver`), Python version, MATLAB version,
  the full command you ran, and the exact error message (screenshot
  or copy-paste, not a paraphrase).
