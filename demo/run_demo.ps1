# Config Drift Detector — Class Demo Script
# Run from: C:\Users\mural\Desktop\ASE
# Usage: .\demo\run_demo.ps1

$Root = Split-Path $PSScriptRoot -Parent

function Show-Banner($title, $color) {
    Write-Host ""
    Write-Host ("=" * 65) -ForegroundColor $color
    Write-Host "  $title" -ForegroundColor $color
    Write-Host ("=" * 65) -ForegroundColor $color
    Write-Host ""
}

function Run-Scenario($label, $src, $cfg, $lang, $color) {
    Show-Banner $label $color
    & python "$Root\main.py" --source $src --config $cfg --languages $lang
    Write-Host ""
    Write-Host "Press Enter to continue to next scenario..." -ForegroundColor DarkGray
    Read-Host | Out-Null
}

Write-Host ""
Write-Host "  CONFIG DRIFT DETECTOR — LIVE DEMO" -ForegroundColor Cyan
Write-Host "  HAW Kiel, Advanced Software Engineering" -ForegroundColor Cyan
Write-Host "  Showing LOW / MEDIUM / HIGH drift levels" -ForegroundColor Cyan

Run-Scenario `
    "SCENARIO 1 of 3 — LOW DRIFT  (score 1-3)" `
    "$Root\demo\low\src" `
    "$Root\demo\low\config" `
    "python" `
    "Green"

Run-Scenario `
    "SCENARIO 2 of 3 — MEDIUM DRIFT  (score 4-9)" `
    "$Root\demo\medium\src" `
    "$Root\demo\medium\config" `
    "python" `
    "Yellow"

Run-Scenario `
    "SCENARIO 3 of 3 — HIGH DRIFT  (score 10+)" `
    "$Root\demo\high\src" `
    "$Root\demo\high\config" `
    "python,java" `
    "Red"

Show-Banner "DEMO COMPLETE" "Cyan"
Write-Host "  Scoring recap:" -ForegroundColor White
Write-Host "    LOW    = score 1-3   (warnings only, or 1 critical)" -ForegroundColor Green
Write-Host "    MEDIUM = score 4-9   (2-3 criticals, or mix)" -ForegroundColor Yellow
Write-Host "    HIGH   = score 10+   (4+ criticals or many missing)" -ForegroundColor Red
Write-Host "    Score  = 3 pts per critical + 1 pt per warning" -ForegroundColor White
Write-Host ""
