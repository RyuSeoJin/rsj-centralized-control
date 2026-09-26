[CmdletBinding()]
param(
    [string]$SdkRoot = (Join-Path $env:LOCALAPPDATA 'Android\Sdk'),
    [string]$AvdName
)

$ErrorActionPreference = 'Stop'
$problems = [System.Collections.Generic.List[string]]::new()

if (-not $IsWindows) {
    $problems.Add('Windows에서 실행해야 합니다.')
}

$tools = @{
    'adb' = Join-Path $SdkRoot 'platform-tools\adb.exe'
    'emulator' = Join-Path $SdkRoot 'emulator\emulator.exe'
}

foreach ($entry in $tools.GetEnumerator()) {
    if (-not (Test-Path -LiteralPath $entry.Value -PathType Leaf)) {
        $problems.Add("$($entry.Key) 도구를 찾지 못했습니다: $($entry.Value)")
    }
}

if ($problems.Count -gt 0) {
    $problems | ForEach-Object { Write-Error $_ }
    exit 1
}

$avds = & $tools.emulator -list-avds
if ($LASTEXITCODE -ne 0) {
    Write-Error 'AVD 목록을 읽지 못했습니다.'
    exit 1
}

Write-Output "SDK 경로: $SdkRoot"
Write-Output "adb: $(& $tools.adb version | Select-Object -First 1)"
Write-Output "emulator: $(& $tools.emulator -version | Select-Object -First 1)"
Write-Output 'AVD:'
if ($avds) {
    $avds | ForEach-Object { Write-Output "- $_" }
} else {
    Write-Output '- 없음'
}

if ($AvdName -and $avds -notcontains $AvdName) {
    Write-Error "요청한 AVD를 찾지 못했습니다: $AvdName"
    exit 1
}
