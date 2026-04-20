#Requires -Version 5.1

# StaMPS Windows Installer — downloads + verifies + unpacks the release zip,
# builds Triangle from vendored source, probes system readiness.

param(
    # Repository slug as "<owner>/<repo>". Default empty so the git-config
    # fallback fires when the script runs from a clone (auto-detect from
    # remote URL). Pass explicitly only when running outside a git checkout
    # or to override the detected slug.
    [string]$Repo = "",
    [string]$Version = "latest",
    [string]$InstallDir = $PSScriptRoot,
    [switch]$SkipAttestation,
    [switch]$IAcceptUnverifiedRisk,
    [switch]$EnableLongPaths,
    [switch]$Force,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

# --- Prerequisite: detect WSL context and abort ---
# $ErrorActionPreference = "Stop" below makes Write-Error terminate the
# script with exit code 1 before our explicit `exit 2` runs. We want
# a specific exit code per failure mode, so write via Host + explicit exit.
if ($env:WSL_DISTRO_NAME -or (Test-Path "/proc/version" -ErrorAction SilentlyContinue)) {
    [Console]::Error.WriteLine("ERROR: Running inside WSL. Use the Linux install flow, not install-windows.ps1.")
    exit 2
}

# --- Prerequisite: force TLS 1.2 (Windows PowerShell 5.1 defaults to 1.0) ---
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# --- Prerequisite: detect elevated context ---
# Used by the long-paths auto-enable flow below and for warning messaging
# when the user is NOT elevated.
$isAdmin = $false
try {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    $isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
} catch {
    # GetCurrent() can fail on locked-down systems; treat as non-admin.
    $isAdmin = $false
}

# --- Prerequisite: long-path registry probe ---
$lp = Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' `
                       -Name LongPathsEnabled -ErrorAction SilentlyContinue
if (-not $lp -or $lp.LongPathsEnabled -ne 1) {
    if ($EnableLongPaths -and $isAdmin) {
        Write-Host "Enabling LongPathsEnabled=1 (HKLM\SYSTEM\CurrentControlSet\Control\FileSystem)..."
        if (-not $DryRun) {
            Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' `
                             -Name LongPathsEnabled -Value 1
            Write-Host "LongPathsEnabled set. Already-running processes must restart to pick up the change."
        }
    } elseif ($EnableLongPaths -and -not $isAdmin) {
        Write-Warning "-EnableLongPaths requires an elevated PowerShell session; skipping registry write."
        Write-Warning "Re-run from an admin shell, or enable manually:"
        Write-Warning "  Set-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled -Value 1"
    } else {
        Write-Warning "Windows LongPathsEnabled is disabled. Deep PATCH_N directories may fail."
        if (-not $isAdmin) {
            Write-Warning "long paths not auto-enabled; StaMPS uses \\?\ prefix internally but filesystem enumeration from Explorer will still 260-char-fail"
        }
        Write-Warning "To enable now, re-run this installer elevated with -EnableLongPaths, or manually:"
        Write-Warning "  Set-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled -Value 1"
        Write-Warning "Alternative: install under a short path (e.g. C:\StaMPS)."
    }
}

# --- Prerequisite: path-in-OneDrive warning ---
if ($InstallDir -match "OneDrive" -or $PSScriptRoot -match "OneDrive") {
    Write-Warning "Install path is inside OneDrive. Sync locks may cause intermittent failures."
}

# --- Prerequisite: non-ASCII path warning ---
if ($InstallDir -cnotmatch '^[\x20-\x7E]+$') {
    Write-Warning "Install path contains non-ASCII characters. Some downstream C++ binaries may fail to open files."
}

# --- Pre-existing install detection ---
# If the install directory already contains a StaMPS binary, require
# either -Force (to overwrite) or prompt the user to pick a different
# -InstallDir. The sentinel file (bin\mt_prep_snap.bat) is present on
# any past successful install; its presence means an extract over the
# top would silently mix old + new binaries.
$sentinel = Join-Path $InstallDir 'bin\mt_prep_snap.bat'
if ((Test-Path $sentinel) -and -not $DryRun) {
    if ($Force) {
        Write-Warning "Existing install at $InstallDir detected; -Force passed, overwriting in place."
    } else {
        [Console]::Error.WriteLine("Existing install at $InstallDir. Use -Force to overwrite or -InstallDir to pick another location.")
        exit 6
    }
}

# --- Resolve GitHub Actions release URL ---
# Prefer the -Repo parameter (must be passed explicitly); otherwise parse
# `fork` or `origin` remote URL when running inside a git checkout. Fail
# clearly if neither source provides a slug.
if ([string]::IsNullOrWhiteSpace($Repo)) {
    $gitCmd = Get-Command git -ErrorAction SilentlyContinue
    if (-not $gitCmd) {
        [Console]::Error.WriteLine("ERROR: git not on PATH and -Repo not specified. Pass -Repo '<owner>/<name>'.")
        exit 1
    }
    $remoteUrl = & git -C "$PSScriptRoot" config --get remote.fork.url 2>$null
    if (-not $remoteUrl) {
        $remoteUrl = & git -C "$PSScriptRoot" config --get remote.origin.url 2>$null
    }
    if ($remoteUrl -match 'github\.com[/:]([^/]+/[^/]+?)(\.git)?$') {
        $Repo = $Matches[1]
        Write-Host "Auto-detected repo slug from git remote: $Repo"
    } else {
        [Console]::Error.WriteLine("ERROR: Cannot determine GitHub repo slug. Pass -Repo '<owner>/<name>'.")
        exit 1
    }
}
$apiUrl = "https://api.github.com/repos/$Repo/releases"
if ($Version -eq "latest") { $apiUrl += "/latest" } else { $apiUrl += "/tags/$Version" }

Write-Host "Fetching release info from $apiUrl..."
$headers = @{}
# GITHUB_TOKEN is used only for rate-limiting against api.github.com.
# MaximumRedirection 2 caps redirect bouncing to known hosts.
if ($env:GITHUB_TOKEN) { $headers["Authorization"] = "Bearer $env:GITHUB_TOKEN" }
$proxyArgs = @{}
if ($env:HTTPS_PROXY -or $env:HTTP_PROXY) {
    # `??` (null-coalesce) is PowerShell 7+; this script declares
    # #Requires -Version 5.1 so we use if-else instead.
    if ($env:HTTPS_PROXY) {
        $proxyArgs["Proxy"] = $env:HTTPS_PROXY
    } else {
        $proxyArgs["Proxy"] = $env:HTTP_PROXY
    }
    $proxyArgs["ProxyUseDefaultCredentials"] = $true
}
$proxyArgs["MaximumRedirection"] = 2

try {
    $release = Invoke-RestMethod -Uri $apiUrl -Headers $headers @proxyArgs
} catch {
    Write-Error "Failed to fetch release. Common causes: TLS issue, proxy, offline, no tag yet."
    Write-Error "Error: $_"
    if (-not $release) {
        Write-Host ""
        Write-Host "No release available yet. Build from source:"
        Write-Host "  cd src && cmake -B build -G `"Visual Studio 17 2022`""
        Write-Host "  cmake --build build --config Release"
        exit 3
    }
    throw
}

$asset = $release.assets | Where-Object { $_.name -eq "stamps-windows-x64-msvc.zip" } | Select-Object -First 1
if (-not $asset) { Write-Error "Release $($release.tag_name) does not contain stamps-windows-x64-msvc.zip"; exit 3 }
$sums = $release.assets | Where-Object { $_.name -eq "SHA256SUMS-msvc" } | Select-Object -First 1

# --- Integrity-proof precondition ---
# SHA256 verification is MANDATORY. If the release lacks a SHA256SUMS-msvc
# asset we refuse to install unless the user explicitly opts out via
# -IAcceptUnverifiedRisk. This plugs the prior hole where $sums being $null
# silently bypassed the hash check.
if (-not $sums) {
    if ($IAcceptUnverifiedRisk) {
        Write-Warning "Release asset SHA256SUMS-msvc missing but -IAcceptUnverifiedRisk was passed. Proceeding WITHOUT integrity proof."
    } else {
        Write-Error "Release asset SHA256SUMS-msvc missing; refusing to install without integrity proof"
        exit 3
    }
}

$zipPath = Join-Path $env:TEMP $asset.name
Write-Host "Downloading $($asset.name) ($([math]::Round($asset.size/1MB,1)) MB)..."

# Wrap the download + verify + extract flow so the staging zip is deleted
# even if any step throws. The previous code only cleaned up on success,
# leaving multi-hundred-megabyte artefacts in %TEMP% after any failure.
try {
    if (-not $DryRun) {
        Invoke-WebRequest -Uri $asset.browser_download_url -OutFile "$zipPath" @proxyArgs
    }

    # --- Verify SHA256 (mandatory) ---
    if ($sums -and -not $DryRun) {
        $expected = (Invoke-RestMethod -Uri $sums.browser_download_url @proxyArgs) -split ' ' | Select-Object -First 1
        $actual = (Get-FileHash -Algorithm SHA256 "$zipPath").Hash.ToLower()
        if ($actual -ne $expected.ToLower()) {
            Write-Error "SHA256 mismatch: expected $expected, got $actual. Aborting."
            exit 4
        }
        Write-Host "SHA256 verified: $actual"
    }

    # --- Verify Sigstore attestation (H1 mitigation, with retry + opt-out) ---
    if (-not $SkipAttestation -and -not $DryRun) {
        $gh = Get-Command gh -ErrorAction SilentlyContinue
        if (-not $gh) {
            Write-Warning "gh CLI not found; skipping Sigstore attestation verification. Install gh for stronger integrity guarantees: https://cli.github.com"
        } else {
            $owner = $Repo.Split('/')[0]

            # Pin the OIDC issuer to GitHub Actions' token endpoint so an
            # attestation signed by a different workflow identity (e.g. a
            # personal PAT-driven release) won't verify. gh 2.50+ supports
            # --cert-oidc-issuer; detect at runtime and degrade gracefully
            # with a loud warning when the flag is unavailable.
            $ghHelp = & gh attestation verify --help 2>&1 | Out-String
            $supportsIssuerPin = $ghHelp -match '--cert-oidc-issuer'
            if (-not $supportsIssuerPin) {
                Write-Warning "gh CLI lacks --cert-oidc-issuer (pre-2.50); trust root is not pinned to GitHub Actions. Upgrade gh for stronger guarantees."
            }

            $verified = $false
            for ($attempt = 1; $attempt -le 3; $attempt++) {
                Write-Host "Verifying Sigstore attestation (attempt $attempt/3)..."
                if ($supportsIssuerPin) {
                    & gh attestation verify "$zipPath" --owner "$owner" --cert-oidc-issuer "https://token.actions.githubusercontent.com"
                } else {
                    & gh attestation verify "$zipPath" --owner "$owner"
                }
                if ($LASTEXITCODE -eq 0) { $verified = $true; break }
                if ($attempt -lt 3) {
                    Write-Warning "Attestation verify failed (transient? retrying in 2s)"
                    Start-Sleep -Seconds 2
                }
            }
            if (-not $verified) {
                if ($IAcceptUnverifiedRisk) {
                    Write-Warning "Attestation verification failed 3x but -IAcceptUnverifiedRisk was passed. Proceeding at your risk."
                } else {
                    Write-Error @"
Sigstore attestation verification failed 3 times.
The artifact may be tampered with, OR github attestations API may be
transiently down. To proceed at your own risk (e.g., on an offline
install), re-run with -IAcceptUnverifiedRisk.
"@
                    exit 5
                }
            } else {
                Write-Host "Attestation verified."
            }
        }
    }

    # --- Unpack ---
    if (-not $DryRun) {
        Write-Host "Unpacking to $InstallDir..."
        Expand-Archive -Path "$zipPath" -DestinationPath "$InstallDir" -Force
    }
} finally {
    # Always clean the temp zip, success or failure. -ErrorAction
    # SilentlyContinue so cleanup itself can't mask the original
    # exception when the finally block runs during a throw.
    if (Test-Path "$zipPath") {
        Remove-Item "$zipPath" -ErrorAction SilentlyContinue
    }
}

# --- Build Triangle from vendored source ---
$triangleDir = Join-Path $InstallDir "external\triangle"
if (Test-Path "$triangleDir") {
    Write-Host "Building Triangle from vendored source..."
    Write-Host ""
    Write-Host "NOTE: Triangle is freely available for research use but requires"
    Write-Host "the author's consent for commercial use. By continuing, you"
    Write-Host "accept Triangle's license (see external\triangle\LICENSE.txt)."
    Write-Host ""
    if (-not $DryRun) {
        Push-Location "$triangleDir"
        cmake -B build -DCMAKE_BUILD_TYPE=Release
        cmake --build build --config Release
        cmake --install build --prefix .
        Pop-Location
    }
}

Write-Host ""
Write-Host "Installation complete."
Write-Host "Dot-source StaMPS_CONFIG.ps1 in your PowerShell session:"
Write-Host "  . $InstallDir\StaMPS_CONFIG.ps1"
