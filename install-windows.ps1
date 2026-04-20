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
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

# --- Prerequisite: detect WSL context and abort ---
if ($env:WSL_DISTRO_NAME -or (Test-Path "/proc/version" -ErrorAction SilentlyContinue)) {
    Write-Error "Running inside WSL. Use the Linux install flow, not install-windows.ps1."
    exit 2
}

# --- Prerequisite: force TLS 1.2 (Windows PowerShell 5.1 defaults to 1.0) ---
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# --- Prerequisite: long-path registry probe ---
$lp = Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' `
                       -Name LongPathsEnabled -ErrorAction SilentlyContinue
if (-not $lp -or $lp.LongPathsEnabled -ne 1) {
    Write-Warning "Windows LongPathsEnabled is disabled. Deep PATCH_N directories may fail."
    Write-Warning "To enable (admin required):"
    Write-Warning "  Set-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled -Value 1"
    Write-Warning "Alternative: install under a short path (e.g. C:\StaMPS)."
}

# --- Prerequisite: path-in-OneDrive warning ---
if ($InstallDir -match "OneDrive" -or $PSScriptRoot -match "OneDrive") {
    Write-Warning "Install path is inside OneDrive. Sync locks may cause intermittent failures."
}

# --- Prerequisite: non-ASCII path warning ---
if ($InstallDir -cnotmatch '^[\x20-\x7E]+$') {
    Write-Warning "Install path contains non-ASCII characters. Some downstream C++ binaries may fail to open files."
}

# --- Resolve GitHub Actions release URL ---
# Prefer the -Repo parameter (must be passed explicitly); otherwise parse
# `fork` or `origin` remote URL when running inside a git checkout. Fail
# clearly if neither source provides a slug.
if ([string]::IsNullOrWhiteSpace($Repo)) {
    $gitCmd = Get-Command git -ErrorAction SilentlyContinue
    if (-not $gitCmd) {
        Write-Error "git not on PATH and -Repo not specified. Pass -Repo '<owner>/<name>'."
        exit 1
    }
    $remoteUrl = & git -C $PSScriptRoot config --get remote.fork.url 2>$null
    if (-not $remoteUrl) {
        $remoteUrl = & git -C $PSScriptRoot config --get remote.origin.url 2>$null
    }
    if ($remoteUrl -match 'github\.com[/:]([^/]+/[^/]+?)(\.git)?$') {
        $Repo = $Matches[1]
        Write-Host "Auto-detected repo slug from git remote: $Repo"
    } else {
        Write-Error "Cannot determine GitHub repo slug. Pass -Repo '<owner>/<name>'."
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
    $proxyArgs["Proxy"] = $env:HTTPS_PROXY ?? $env:HTTP_PROXY
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

$zipPath = Join-Path $env:TEMP $asset.name
Write-Host "Downloading $($asset.name) ($([math]::Round($asset.size/1MB,1)) MB)..."
if (-not $DryRun) {
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zipPath @proxyArgs
}

# --- Verify SHA256 ---
if ($sums -and -not $DryRun) {
    $expected = (Invoke-RestMethod -Uri $sums.browser_download_url @proxyArgs) -split ' ' | Select-Object -First 1
    $actual = (Get-FileHash -Algorithm SHA256 $zipPath).Hash.ToLower()
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
        $verified = $false
        for ($attempt = 1; $attempt -le 3; $attempt++) {
            Write-Host "Verifying Sigstore attestation (attempt $attempt/3)..."
            & gh attestation verify $zipPath --owner $owner
            if ($LASTEXITCODE -eq 0) { $verified = $true; break }
            if ($attempt -lt 3) {
                Write-Warning "Attestation verify failed (transient? retrying in 2s)"
                Start-Sleep -Seconds 2
            }
        }
        if (-not $verified) {
            if ($IAcceptUnverifiedRisk) {
                Write-Warning "Attestation verification failed 3× but -IAcceptUnverifiedRisk was passed. Proceeding at your risk."
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
    Expand-Archive -Path $zipPath -DestinationPath $InstallDir -Force
    Remove-Item $zipPath
}

# --- Build Triangle from vendored source ---
$triangleDir = Join-Path $InstallDir "external\triangle"
if (Test-Path $triangleDir) {
    Write-Host "Building Triangle from vendored source..."
    Write-Host ""
    Write-Host "NOTE: Triangle is freely available for research use but requires"
    Write-Host "the author's consent for commercial use. By continuing, you"
    Write-Host "accept Triangle's license (see external\triangle\LICENSE.txt)."
    Write-Host ""
    if (-not $DryRun) {
        Push-Location $triangleDir
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
