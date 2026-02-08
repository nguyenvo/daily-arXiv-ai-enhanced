
$env:MODEL_NAME="gemini-2.0-flash"
$dataDate = "2026-02-07"
$inputFile = "data/${dataDate}.jsonl"
$outputFile = "data/${dataDate}_AI_enhanced_English.jsonl"

Write-Host "--- Clearing old output ---"
if (Test-Path $outputFile) { Remove-Item $outputFile }

Write-Host "--- Running Enhance ---"
Set-Location ai
python enhance.py --data "../$inputFile" --max_workers 5 --limit 3
Set-Location ..

Write-Host "--- Checking Output ---"
if (Test-Path $outputFile) {
    Get-Item $outputFile
    Write-Host "--- Running Convert ---"
    Set-Location to_md
    python convert.py --data "../$outputFile"
    Set-Location ..
} else {
    Write-Error "Enhance failed to create $outputFile"
}
