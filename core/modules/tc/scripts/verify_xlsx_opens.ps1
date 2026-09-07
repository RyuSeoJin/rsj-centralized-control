# verify_xlsx_opens.ps1 — 생성한 xlsx가 Excel에서 '복구' 프롬프트 없이 열리는지 검증한다.
#
# openpyxl로 만든 파일은 XML이 올바로 파싱되어도 Excel 스키마를 어겨 복구 대상이 될 수 있다
# (2026-08-02 사례: 틀 고정 해제 시 남은 selection / 데이터 검증식의 '=' 접두 /
#  '='로 시작하는 설명 문구). 파싱 검사만으로는 잡히지 않으므로 실제 Excel로 열어 확인한다.
#
# 사용법:
#   powershell -ExecutionPolicy Bypass -File verify_xlsx_opens.ps1 <파일경로> [<파일경로> ...]
#
# 종료 코드: 전부 정상이면 0, 하나라도 실패하면 1

param([Parameter(Mandatory = $true, ValueFromRemainingArguments = $true)][string[]]$Paths)

$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
$failed = 0

foreach ($p in $Paths) {
    $full = (Resolve-Path $p -ErrorAction SilentlyContinue)
    if ($null -eq $full) {
        Write-Output ("[MISSING]  " + $p)
        $failed = 1
        continue
    }
    try {
        $wb = $excel.Workbooks.Open($full.Path)
        if ($null -eq $wb) {
            Write-Output ("[FAIL]     " + $full.Path + "  (복구 필요 — 열리지 않음)")
            $failed = 1
        }
        else {
            $names = @()
            foreach ($ws in $wb.Worksheets) { $names += $ws.Name }
            Write-Output ("[OK]       " + (Split-Path $full.Path -Leaf) + "  sheets: " + ($names -join " / "))
            $wb.Close($false)
        }
    }
    catch {
        Write-Output ("[FAIL]     " + $full.Path + "  :: " + $_.Exception.Message)
        $failed = 1
    }
}

$excel.Quit()
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null
if ($failed -ne 0) { exit 1 }
