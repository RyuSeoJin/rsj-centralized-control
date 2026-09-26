[CmdletBinding()]
param(
    [string]$SdkRoot = (Join-Path $env:LOCALAPPDATA 'Android\Sdk'),
    [switch]$AcceptSdkLicenses
)

$ErrorActionPreference = 'Stop'
$moduleRoot = Split-Path -Parent $PSScriptRoot
$manifestPath = Join-Path $moduleRoot 'manifests\android-studio-windows.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json

if (-not $IsWindows) {
    throw 'Windows에서만 실행할 수 있습니다.'
}
if (-not $AcceptSdkLicenses) {
    throw 'Android SDK 라이선스를 직접 확인한 뒤 -AcceptSdkLicenses 옵션으로 다시 실행해야 합니다.'
}
if (-not (Test-Path -LiteralPath $SdkRoot -PathType Container)) {
    throw "Android SDK 경로를 찾지 못했습니다: $SdkRoot"
}

$studioJbr = Join-Path $env:ProgramFiles 'Android\Android Studio\jbr'
if (-not (Test-Path -LiteralPath (Join-Path $studioJbr 'bin\java.exe') -PathType Leaf)) {
    throw "Android Studio의 내장 Java를 찾지 못했습니다: $studioJbr"
}
$env:JAVA_HOME = $studioJbr
$env:ANDROID_SDK_ROOT = $SdkRoot

$toolsRoot = Join-Path $SdkRoot 'cmdline-tools'
$toolsPath = Join-Path $toolsRoot 'latest'
$sdkManager = Join-Path $toolsPath 'bin\sdkmanager.bat'
$avdManager = Join-Path $toolsPath 'bin\avdmanager.bat'

function Test-Hash {
    param([string]$Path, [string]$Expected)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }
    return ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -eq $Expected.ToLowerInvariant())
}

if (-not (Test-Path -LiteralPath $sdkManager -PathType Leaf)) {
    if (Test-Path -LiteralPath $toolsPath) {
        throw "기존 명령줄 도구 위치가 완전하지 않습니다: $toolsPath"
    }
    $latestDownloads = & (Join-Path $PSScriptRoot 'get-latest-android-downloads.ps1')
    $tool = $latestDownloads.commandLineTools
    $cache = Join-Path $env:TEMP 'android-emulator-commandline-tools'
    New-Item -ItemType Directory -Force -Path $cache | Out-Null
    $archive = Join-Path $cache $tool.fileName
    if (-not (Test-Hash -Path $archive -Expected $tool.sha256)) {
        if (Test-Path -LiteralPath $archive -PathType Leaf) { Remove-Item -LiteralPath $archive -Force }
        Write-Output 'Android SDK 명령줄 도구를 내려받습니다.'
        & curl.exe --fail --location --output $archive $tool.downloadUrl
        if ($LASTEXITCODE -ne 0) { throw 'Android SDK 명령줄 도구를 내려받지 못했습니다.' }
    }
    if (-not (Test-Hash -Path $archive -Expected $tool.sha256)) {
        throw 'Android SDK 명령줄 도구의 SHA-256이 manifest와 다릅니다.'
    }
    $extract = Join-Path $cache ('extract-' + [guid]::NewGuid().ToString('N'))
    Expand-Archive -LiteralPath $archive -DestinationPath $extract
    $source = Join-Path $extract 'cmdline-tools'
    if (-not (Test-Path -LiteralPath (Join-Path $source 'bin\sdkmanager.bat') -PathType Leaf)) {
        throw '명령줄 도구 압축 파일의 구조가 예상과 다릅니다.'
    }
    New-Item -ItemType Directory -Force -Path $toolsRoot | Out-Null
    Move-Item -LiteralPath $source -Destination $toolsPath
}

if (-not (Test-Path -LiteralPath $avdManager -PathType Leaf)) {
    throw "avdmanager를 찾지 못했습니다: $avdManager"
}

$yes = 1..200 | ForEach-Object { 'y' }
$yes | & $sdkManager "--sdk_root=$SdkRoot" --licenses | Out-Host
if ($LASTEXITCODE -ne 0) { throw 'Android SDK 라이선스를 수락하지 못했습니다.' }

$availablePackages = & $sdkManager "--sdk_root=$SdkRoot" --list
if ($LASTEXITCODE -ne 0) { throw '설치 가능한 Android SDK 패키지 목록을 읽지 못했습니다.' }
$imageCandidates = [regex]::Matches(($availablePackages -join "`n"), 'system-images;android-(?<api>\d+);google_apis;x86_64') |
    ForEach-Object { [pscustomobject]@{ api = [int]$_.Groups['api'].Value; package = $_.Value } } |
    Sort-Object -Property api -Descending
if (-not $imageCandidates) { throw '설치 가능한 숫자 API의 Google APIs x86_64 System Image를 찾지 못했습니다.' }
$image = $imageCandidates[0].package
$apiLevel = $imageCandidates[0].api
Write-Output "SDK 구성 요소와 System Image를 설치합니다: $image"
& $sdkManager "--sdk_root=$SdkRoot" --install 'platform-tools' 'emulator' $image
if ($LASTEXITCODE -ne 0) { throw 'Android SDK 구성 요소를 설치하지 못했습니다.' }

$avdName = $manifest.defaultAvd.avdNameTemplate -replace '\{api\}', $apiLevel
$existing = & (Join-Path $SdkRoot 'emulator\emulator.exe') -list-avds
if ($existing -notcontains $avdName) {
    Write-Output "AVD를 만듭니다: $avdName"
    'no' | & $avdManager create avd --force --name $avdName --package $image --device $manifest.defaultAvd.deviceProfile
    if ($LASTEXITCODE -ne 0) { throw 'AVD를 만들지 못했습니다.' }
}

& (Join-Path $PSScriptRoot 'verify-android.ps1') -SdkRoot $SdkRoot -AvdName $avdName
exit $LASTEXITCODE
