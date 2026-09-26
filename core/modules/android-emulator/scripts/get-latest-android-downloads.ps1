[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$moduleRoot = Split-Path -Parent $PSScriptRoot
$manifestPath = Join-Path $moduleRoot 'manifests\android-studio-windows.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$sourcePage = $manifest.officialSources.studioPage

if (-not $sourcePage) {
    throw 'manifest에 Android 공식 다운로드 페이지가 없습니다.'
}

try {
    $content = (Invoke-WebRequest -UseBasicParsing -Uri $sourcePage).Content
} catch {
    throw "Android 공식 다운로드 페이지를 읽지 못했습니다: $sourcePage`n$($_.Exception.Message)"
}

function Get-DownloadMetadata {
    param(
        [string]$ModalId,
        [string]$FilePattern
    )

    $rowPattern = '(?is)<tr\b[^>]*>.*?data-modal-dialog-id="' + [regex]::Escape($ModalId) + '"[^>]*>\s*(?<file>' + $FilePattern + ')\s*</button>.*?<td>\s*(?<sha>[a-f0-9]{64})\s*</td>.*?</tr>'
    $row = [regex]::Match($content, $rowPattern)
    if (-not $row.Success) {
        throw "공식 다운로드 표에서 $ModalId 항목을 찾지 못했습니다. 페이지 구조가 바뀌었을 수 있습니다."
    }

    $fileName = $row.Groups['file'].Value.Trim()
    $sha256 = $row.Groups['sha'].Value.ToLowerInvariant()
    $urlPattern = 'https://[^"''\s<]+' + [regex]::Escape('/' + $fileName)
    $url = [regex]::Match($content, $urlPattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    if (-not $url.Success) {
        throw "공식 페이지에서 $fileName 파일의 다운로드 URL을 찾지 못했습니다."
    }

    [pscustomobject]@{
        fileName = $fileName
        sha256 = $sha256
        downloadUrl = [System.Net.WebUtility]::HtmlDecode($url.Value)
    }
}

[pscustomobject]@{
    androidStudio = Get-DownloadMetadata -ModalId 'studio_win_notools_exe_download' -FilePattern 'android-studio-[^<]+?-windows\.exe'
    commandLineTools = Get-DownloadMetadata -ModalId 'sdk_win_download' -FilePattern 'commandlinetools-win-[^<]+?_latest\.zip'
    sourcePage = $sourcePage
}
