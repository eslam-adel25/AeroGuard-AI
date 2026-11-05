$ErrorActionPreference = "Stop"

if (-not [System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform(
    [System.Runtime.InteropServices.OSPlatform]::Windows
)) {
    throw "This installer supports Windows only."
}

$assetName = switch ([System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()) {
    "X64" { "go2rtc_win64.zip" }
    "X86" { "go2rtc_win32.zip" }
    "Arm64" { "go2rtc_win_arm64.zip" }
    default { throw "Unsupported Windows architecture: $([System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture)" }
}

$release = Invoke-RestMethod `
    -Uri "https://api.github.com/repos/AlexxIT/go2rtc/releases/latest" `
    -Headers @{ "User-Agent" = "AeroGuard-AI local setup" } `
    -TimeoutSec 30
$asset = $release.assets | Where-Object { $_.name -eq $assetName } | Select-Object -First 1
if (-not $asset) {
    throw "The official go2rtc release $($release.tag_name) has no asset for $assetName."
}

$backendRoot = Split-Path -Parent $PSScriptRoot
$toolsPath = Join-Path $backendRoot "tools"
New-Item -ItemType Directory -Path $toolsPath -Force | Out-Null
$temporaryRoot = Join-Path ([System.IO.Path]::GetTempPath()) "go2rtc-$([guid]::NewGuid().ToString('N'))"
$archivePath = Join-Path $temporaryRoot "release.zip"
$extractPath = Join-Path $temporaryRoot "extracted"
New-Item -ItemType Directory -Path $temporaryRoot -Force | Out-Null

try {
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $archivePath -TimeoutSec 120
    Expand-Archive -LiteralPath $archivePath -DestinationPath $extractPath -Force
    $downloadedExecutable = Get-ChildItem -LiteralPath $extractPath -Filter "go2rtc.exe" -File -Recurse | Select-Object -First 1
    if (-not $downloadedExecutable) {
        throw "The downloaded official archive did not contain go2rtc.exe."
    }

    $executable = Join-Path $toolsPath "go2rtc.exe"
    Copy-Item -LiteralPath $downloadedExecutable.FullName -Destination $executable -Force
    Write-Output "Installed go2rtc $($release.tag_name) at $executable"
}
finally {
    if (Test-Path -LiteralPath $temporaryRoot) {
        Remove-Item -LiteralPath $temporaryRoot -Recurse -Force
    }
}
