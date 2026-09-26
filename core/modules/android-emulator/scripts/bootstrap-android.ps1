[CmdletBinding()]
param(
    [string]$DownloadDirectory = (Join-Path $env:TEMP 'android-emulator-installer'),
    [switch]$SkipInstallerLaunch
)

$ErrorActionPreference = 'Stop'
$moduleRoot = Split-Path -Parent $PSScriptRoot
$manifestPath = Join-Path $moduleRoot 'manifests\android-studio-windows.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json

if (-not $IsWindows) {
    throw 'Windows에서만 실행할 수 있습니다.'
}
$installedStudio = Join-Path $env:ProgramFiles 'Android\Android Studio\bin\studio64.exe'
if (Test-Path -LiteralPath $installedStudio -PathType Leaf) {
    Write-Output "Android Studio가 이미 설치되어 있어 설치 마법사를 건너뜁니다: $installedStudio"
    Write-Output 'Android SDK·Emulator·AVD 상태를 점검합니다.'
    & (Join-Path $PSScriptRoot 'verify-android.ps1')
    exit $LASTEXITCODE
}

$latestDownloads = & (Join-Path $PSScriptRoot 'get-latest-android-downloads.ps1')
$studio = $latestDownloads.androidStudio

$systemDrive = Get-PSDrive -Name C
$minimumBytes = [int64]$manifest.minimumHost.freeSpaceGiB * 1GB
if ($systemDrive.Free -lt $minimumBytes) {
    throw "C: 드라이브의 빈 공간이 부족합니다. 최소 $($manifest.minimumHost.freeSpaceGiB)GiB가 필요합니다."
}

New-Item -ItemType Directory -Force -Path $DownloadDirectory | Out-Null
$installerPath = Join-Path $DownloadDirectory $studio.fileName

function Test-InstallerHash {
    param([string]$Path, [string]$Expected)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }
    return ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -eq $Expected.ToLowerInvariant())
}

if (-not (Test-InstallerHash -Path $installerPath -Expected $studio.sha256)) {
    if (Test-Path -LiteralPath $installerPath -PathType Leaf) {
        Remove-Item -LiteralPath $installerPath -Force
    }
    Write-Output "Android Studio 설치 파일을 내려받습니다: $($studio.release)"
    & curl.exe --fail --location --output $installerPath $studio.downloadUrl
    if ($LASTEXITCODE -ne 0) {
        throw 'Android Studio 설치 파일을 내려받지 못했습니다.'
    }
}

if (-not (Test-InstallerHash -Path $installerPath -Expected $studio.sha256)) {
    throw '설치 파일의 SHA-256이 manifest와 다릅니다. 설치를 중단합니다.'
}
Write-Output '설치 파일 SHA-256 확인을 통과했습니다.'

if ($SkipInstallerLaunch) {
    Write-Output "설치 파일 준비 완료: $installerPath"
    exit 0
}

Write-Output 'Android Studio 설치 마법사를 엽니다. SDK 라이선스를 직접 확인하고 표준 설치를 완료해 주세요.'
$installer = Start-Process -FilePath $installerPath -Wait -PassThru
if ($installer.ExitCode -ne 0) {
    throw "Android Studio 설치 프로그램이 종료 코드 $($installer.ExitCode)로 끝났습니다."
}

Write-Output '설치 프로그램이 끝났습니다. Android SDK·Emulator·AVD 상태를 점검합니다.'
& (Join-Path $PSScriptRoot 'verify-android.ps1')
exit $LASTEXITCODE
