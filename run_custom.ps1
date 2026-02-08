# Environment Setup
$env:LANGUAGE = "English"
$env:CATEGORIES = "cs.CL,cs.AI,cs.MA,cs.LG"
$env:MODEL_NAME = "gemini-2.0-flash"
# $env:GOOGLE_API_KEY = "YOUR_KEY_HERE" # User must provide this

Write-Host "=== Custom Daily Paper Feed (Gemini + Vietnamese) ==="

$today = Get-Date -Format "yyyy-MM-dd"
$todayFile = "data/${today}.jsonl"

# 1. Crawl
Write-Host "Step 1: Crawling ${today}..."
if (Test-Path $todayFile) {
    Remove-Item $todayFile
}

Set-Location daily_arxiv
scrapy crawl arxiv -o "../$todayFile"
Set-Location ..

if (-not (Test-Path $todayFile)) {
    Write-Error "Crawling failed."
    exit 1
}

# 2. Deduplication (Skipped) / 2. Loại bỏ trùng lặp (Đã bỏ qua)

# 3. AI Enhance (Gemini)
Write-Host "Step 3: AI Enhancement using $env:MODEL_NAME..."
Set-Location ai
# We use 'Chinese' as a dummy language arg because our script now hardcodes bilingual prompt
# Chúng tôi sử dụng 'Chinese' làm đối số ngôn ngữ giả vì tập lệnh của chúng tôi hiện đã mã hóa cứng lời nhắc song ngữ
python enhance.py --data "../$todayFile" --max_workers 5
Set-Location ..

# 4. Generate Markdown
Write-Host "Step 4: Generating Markdown..."
Set-Location to_md
python convert.py --data "../data/${today}_AI_enhanced_English.jsonl"
Set-Location ..

Write-Host "Done! Check data/${today}_AI_enhanced_English.md"
