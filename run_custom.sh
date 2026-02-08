#!/bin/bash

# Environment Setup
export LANGUAGE="English" # We handle bilingual inside the prompt manually now / Chúng tôi xử lý song ngữ bên trong lời nhắc theo cách thủ công ngay bây giờ
export CATEGORIES="cs.CL,cs.AI,cs.MA,cs.LG"
export MODEL_NAME="gemini-1.5-flash"
# export GOOGLE_API_KEY="YOUR_KEY_HERE" # User must provide this

echo "=== Custom Daily Paper Feed (Gemini + Vietnamese) ==="

today=`date -u "+%Y-%m-%d"`

# 1. Crawl
echo "Step 1: Crawling ${today}..."
if [ -f "data/${today}.jsonl" ]; then
    rm "data/${today}.jsonl"
fi

cd daily_arxiv
scrapy crawl arxiv -o ../data/${today}.jsonl
cd ..

if [ ! -f "data/${today}.jsonl" ]; then
    echo "Crawling failed."
    exit 1
fi

# 2. Deduplication (Optional, skipping for simplicity in this custom run)
# 2. Loại bỏ trùng lặp (Tùy chọn, bỏ qua để đơn giản hóa trong lần chạy tùy chỉnh này)

# 3. AI Enhance (Gemini)
echo "Step 3: AI Enhancement using ${MODEL_NAME}..."
cd ai
# We use 'Chinese' as a dummy language arg because our script now hardcodes bilingual prompt
# Chúng tôi sử dụng 'Chinese' làm đối số ngôn ngữ giả vì tập lệnh của chúng tôi hiện đã mã hóa cứng lời nhắc song ngữ
python enhance.py --data ../data/${today}.jsonl --max_workers 5
cd ..

# 4. Generate Markdown
echo "Step 4: Generating Markdown..."
cd to_md
python convert.py --data ../data/${today}_AI_enhanced_English.jsonl
cd ..

echo "Done! Check data/${today}_AI_enhanced_English.md"

# 5. Send Email (Optional)
if [ -n "$EMAIL_SENDER" ] && [ -n "$EMAIL_PASSWORD" ]; then
    echo "Step 5: Sending Email..."
    python send_email.py --file "data/${today}_AI_enhanced_English.md" --subject "Daily Paper Feed - ${today}"
fi

