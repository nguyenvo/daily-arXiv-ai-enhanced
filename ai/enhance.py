import os
import json
import sys
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict
from queue import Queue
import re
import time
import random
from threading import Lock
import itertools

# List of models to try in order / Danh sách các mô hình để thử theo thứ tự
FALLBACK_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-flash-latest",
    "gemini-pro-latest",
]

# Global lock for model switching to ensure thread safety if needed (though mainly logical)
# Khóa toàn cục để chuyển đổi mô hình nhằm đảm bảo an toàn luồng nếu cần (mặc dù chủ yếu là logic)
# For simplicity in this script, we'll just let each worker try the list.
# Để đơn giản trong tập lệnh này, chúng tôi chỉ để mỗi worker thử danh sách.
# A more complex manager would track global 'cooldowns' for models.
# Một trình quản lý phức tạp hơn sẽ theo dõi "thời gian hồi chiêu" toàn cục cho các mô hình.

# INSERT_YOUR_CODE
import requests

import dotenv
import argparse
from tqdm import tqdm

import langchain_core.exceptions
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from structure import Structure

if os.path.exists('.env'):
    dotenv.load_dotenv()
template = open("template.txt", "r").read()
system = open("system.txt", "r").read()

def parse_args():
    """Parse command line arguments / Phân tích tham số dòng lệnh"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, required=True, help="jsonline data file")
    parser.add_argument("--max_workers", type=int, default=1, help="Maximum number of parallel workers")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of items to process")
    return parser.parse_args()

def get_llm(model_name: str):
    return ChatGoogleGenerativeAI(model=model_name, temperature=0).with_structured_output(Structure)

def process_single_item(item: Dict, language: str) -> Dict:
    def is_sensitive(content: str) -> bool:
        """
        Call spam.dw-dengwei.workers.dev API to check if content contains sensitive words.
        Return True if sensitive words are detected, False otherwise.
        
        Gọi API spam.dw-dengwei.workers.dev để kiểm tra xem nội dung có chứa từ nhạy cảm hay không.
        Trả về True nếu phát hiện từ nhạy cảm, ngược lại là False.
        """
        try:
            resp = requests.post(
                "https://spam.dw-dengwei.workers.dev",
                json={"text": content},
                timeout=5
            )
            if resp.status_code == 200:
                result = resp.json()
                # Convention: interface returns {"sensitive": true/false, ...}
                # Quy ước: giao diện trả về {"sensitive": true/false, ...}
                return result.get("sensitive", True)
            else:
                # If interface error, default to not triggering sensitive words
                # Nếu lỗi giao diện, mặc định không kích hoạt từ nhạy cảm
                print(f"Sensitive check failed with status {resp.status_code}", file=sys.stderr)
                return True
        except Exception as e:
            print(f"Sensitive check error: {e}", file=sys.stderr)
            return True

    def check_github_code(content: str) -> Dict:
        """Extract and verify GitHub links / Trích xuất và xác minh liên kết GitHub"""
        code_info = {}

        # 1. Prioritize matching github.com/owner/repo format
        # 1. Ưu tiên khớp định dạng github.com/owner/repo
        github_pattern = r"https?://github\.com/([a-zA-Z0-9-_]+)/([a-zA-Z0-9-_\.]+)"
        match = re.search(github_pattern, content)
        
        if match:
            owner, repo = match.groups()
            # Clean repo name, remove possible .git suffix or trailing punctuation
            # Làm sạch tên repo, loại bỏ hậu tố .git có thể có hoặc dấu câu ở cuối
            repo = repo.rstrip(".git").rstrip(".,)")
            
            full_url = f"https://github.com/{owner}/{repo}"
            code_info["code_url"] = full_url
            
            # Try calling GitHub API to get information
            # Thử gọi GitHub API để lấy thông tin
            github_token = os.environ.get("TOKEN_GITHUB")
            headers = {"Accept": "application/vnd.github.v3+json"}
            if github_token:
                headers["Authorization"] = f"token {github_token}"
            
            try:
                api_url = f"https://api.github.com/repos/{owner}/{repo}"
                resp = requests.get(api_url, headers=headers, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    code_info["code_stars"] = data.get("stargazers_count", 0)
                    code_info["code_last_update"] = data.get("pushed_at", "")[:10]
            except Exception:
                # API call failure does not affect the main flow
                # Lỗi gọi API không ảnh hưởng đến luồng chính
                pass
            return code_info

        # 2. If no github.com, try matching github.io
        # 2. Nếu không có github.com, thử khớp github.io
        github_io_pattern = r"https?://[a-zA-Z0-9-_]+\.github\.io(?:/[a-zA-Z0-9-_\.]+)*"
        match_io = re.search(github_io_pattern, content)
        
        if match_io:
            url = match_io.group(0)
            # Clean trailing punctuation
            # Làm sạch dấu câu ở cuối
            url = url.rstrip(".,)")
            code_info["code_url"] = url
            # github.io does not check for star and update
            # github.io không kiểm tra star và update
                
        return code_info

    # 1. Sensitive content check / 1. Kiểm tra nội dung nhạy cảm
    if is_sensitive(item.get("summary", "")):
        print(f"Skipping sensitive content: {item['id']}", file=sys.stderr)
        return None

    # 2. Check code availability / 2. Kiểm tra tính khả dụng của mã
    code_info = check_github_code(item.get("summary", ""))
    if code_info:
        item.update(code_info)
    
    default_ai_fields = {
        "tldr": "Summary generation failed",
        "motivation": "Motivation analysis unavailable",
        "method": "Method extraction failed",
        "result": "Result analysis unavailable",
        "conclusion": "Conclusion extraction failed",
        "tldr_vn": "Tóm tắt thất bại",
        "motivation_vn": "Phân tích động lực không khả dụng",
        "method_vn": "Trích xuất phương pháp thất bại",
        "result_vn": "Phân tích kết quả không khả dụng",
        "conclusion_vn": "Trích xuất kết luận thất bại"
    }
    
    global FALLBACK_MODELS
    # Prioritize the configured model, then the others
    # Ưu tiên mô hình đã định cấu hình, sau đó là các mô hình khác
    configured_model = os.environ.get("MODEL_NAME", "gemini-2.0-flash")
    models_to_try = [configured_model] + [m for m in FALLBACK_MODELS if m != configured_model]
    
    max_retries_per_model = 3
    last_exception = None
    success = False

    # Try models in order / Thử các mô hình theo thứ tự
    for model_idx, current_model in enumerate(models_to_try):
        if success: break
        
        try:
            # Re-create chain for the specific model
            # Tạo lại chuỗi cho mô hình cụ thể
            llm = get_llm(current_model)
            prompt_template = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(system),
                HumanMessagePromptTemplate.from_template(template=template)
            ])
            chain = prompt_template | llm
            
            # Retry logic for the CURRENT model
            # Logic thử lại cho mô hình HIỆN TẠI
            for attempt in range(max_retries_per_model):
                try:
                    response: Structure = chain.invoke({
                        "language": language,
                        "content": item['summary']
                    })
                    item['AI'] = response.model_dump()
                    item['AI']['model_used'] = current_model
                    success = True
                    break
                
                except langchain_core.exceptions.OutputParserException as e:
                    # Recovery logic
                    # Logic khôi phục
                    error_msg = str(e)
                    partial_data = {}
                    if "Function Structure arguments:" in error_msg:
                        try:
                            # Extract JSON string / Trích xuất chuỗi JSON
                            json_str = error_msg.split("Function Structure arguments:", 1)[1].strip().split('are not valid JSON')[0].strip()
                            # Pre-process LaTeX math symbols / Tiền xử lý các ký hiệu toán học LaTeX
                            json_str = json_str.replace('\\', '\\\\')
                            # Try to parse repaired JSON / Cố gắng phân tích cú pháp JSON đã sửa
                            partial_data = json.loads(json_str)
                        except Exception:
                            pass
                    
                    if partial_data:
                        item['AI'] = {**default_ai_fields, **partial_data}
                        item['AI']['model_used'] = current_model
                        print(f"Using partial AI data for {item.get('id', 'unknown')}", file=sys.stderr)
                        success = True
                        break
                    else:
                        print(f"Parser failed completely for {item.get('id')}. Error: {e}", file=sys.stderr)
                        raise e 

                except Exception as e:
                    is_rate_limit = "429" in str(e) or "Resource has been exhausted" in str(e)
                    
                    if attempt == max_retries_per_model - 1:
                        print(f"Model {current_model} failed after {max_retries_per_model} attempts. Error: {e}", file=sys.stderr)
                        if model_idx == len(models_to_try) - 1:
                           last_exception = e
                           raise e
                        else:
                            print(f"Switching to next model: {models_to_try[model_idx+1]}", file=sys.stderr)
                            break 
                    
                    sleep_time = (2 ** attempt) + random.uniform(1, 4)
                    match = re.search(r"'retryDelay':\s*'(\d+(\.\d+)?)s'", str(e))
                    if match:
                        delay_s = float(match.group(1))
                        sleep_time = delay_s + 1
                        print(f"Rate limited on {current_model}. Sleeping {sleep_time:.2f}s...", file=sys.stderr)
                    
                    if is_rate_limit and sleep_time > 60:
                         print(f"Wait time too long ({sleep_time}s), trying next model immediately...", file=sys.stderr)
                         break 
                         
                    print(f"Retry {attempt+1}/{max_retries_per_model} on {current_model} for {item.get('id')}", file=sys.stderr)
                    time.sleep(sleep_time)
                    
        except Exception as outer_e:
             # Exception switching models / Ngoại lệ khi chuyển đổi mô hình
             last_exception = outer_e
             continue

    if not success:
        # All models failed / Tất cả các mô hình đều thất bại
        print(f"All models failed for {item.get('id')}: {last_exception}", file=sys.stderr)
        item['AI'] = default_ai_fields
    for v in item.get("AI", {}).values():
        if is_sensitive(str(v)):
             # Sensitive content detected in AI output / Phát hiện nội dung nhạy cảm trong đầu ra AI
            return None
    return item

def process_all_items(data: List[Dict], model_name: str, language: str, max_workers: int, target_file: str = None) -> List[Dict]:
    """Process all items in parallel / Xử lý song song tất cả các mục"""
    if not os.environ.get("GOOGLE_API_KEY"):
        print("GOOGLE_API_KEY not found in environment variables", file=sys.stderr)
        return data

    print('Connect to initial model:', model_name, file=sys.stderr)
    
    # We now instantiate the chain inside process_single_item to handle model switching
    # Bây giờ chúng ta khởi tạo chuỗi bên trong process_single_item để xử lý việc chuyển đổi mô hình
    
    processed_data = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit tasks / Gửi tác vụ
        future_to_item = {
            executor.submit(process_single_item, item, language): item 
            for item in data
        }
        
        # Use tqdm to show progress / Sử dụng tqdm để hiển thị tiến độ
        for future in tqdm(as_completed(future_to_item), total=len(data), desc="Processing items"):
            item = future_to_item[future]
            try:
                result = future.result()
                processed_data.append(result)
                if target_file and result:
                    with open(target_file, "a", encoding='utf-8') as f:
                        f.write(json.dumps(result) + "\n")
            except Exception as exc:
                print(f"Unexpected error for {item['id']}: {exc}", file=sys.stderr)
                # Keep original data even if failed / Giữ lại dữ liệu gốc ngay cả khi thất bại
                processed_data.append(item)
    
    return processed_data

def main():
    args = parse_args()
    model_name = os.environ.get("MODEL_NAME", 'gemini-1.5-flash')
    language = os.environ.get("LANGUAGE", 'Chinese')

    # Check and delete target file - MODIFIED: Support incremental processing
    # Kiểm tra và xóa tệp đích - ĐÃ SỬA ĐỔI: Hỗ trợ xử lý tăng dần
    target_file = args.data.replace('.jsonl', f'_AI_enhanced_{language}.jsonl')
    
    # Load existing processed IDs if file exists / Tải các ID đã xử lý nếu tệp tồn tại
    processed_ids = set()
    if os.path.exists(target_file):
        print(f"Found existing file {target_file}, loading processed items...", file=sys.stderr)
        try:
            with open(target_file, "r") as f:
                for line in f:
                    try:
                        existing_item = json.loads(line)
                        # Only consider it processed if it has valid AI fields (check logic specific to your needs)
                        # Chỉ coi là đã xử lý nếu nó có các trường AI hợp lệ (kiểm tra logic cụ thể theo nhu cầu của bạn)
                        # Here we assume if 'AI' exists and 'tldr' is not the failure message
                        # Ở đây chúng tôi giả định nếu 'AI' tồn tại và 'tldr' không phải là thông báo lỗi
                        ai_data = existing_item.get('AI', {})
                        if ai_data.get('tldr') != "Summary generation failed":
                             processed_ids.add(existing_item['id'])
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error reading existing file: {e}", file=sys.stderr)
    
    # if os.path.exists(target_file):
    #     os.remove(target_file)
    #     print(f'Removed existing file: {target_file}', file=sys.stderr)

    # Read data / Đọc dữ liệu
    data = []
    with open(args.data, "r", encoding='utf-8') as f:
        for line in f:
            data.append(json.loads(line))

    # Deduplication / Loại bỏ trùng lặp
    seen_ids = set()
    unique_data = []
    for item in data:
        if item['id'] not in seen_ids:
            seen_ids.add(item['id'])
            unique_data.append(item)

    
    # Filter out already processed items / Lọc ra các mục đã được xử lý
    data = unique_data
    items_to_process = [item for item in data if item['id'] not in processed_ids]
    
    print(f"Total items: {len(data)}, Already processed: {len(processed_ids)}, Remaining: {len(items_to_process)}", file=sys.stderr)
    
    if args.limit:
        items_to_process = items_to_process[:args.limit]
    print('Open:', args.data, file=sys.stderr)
    
    # Process all data in parallel / Xử lý song song tất cả dữ liệu
    new_processed_data = process_all_items(
        items_to_process,
        model_name,
        language,
        args.max_workers,
        target_file=target_file
    )
    
    # Append new results to file / Nối kết quả mới vào tệp
    # Results are now saved incrementally
    # with open(target_file, "a", encoding='utf-8') as f:
    #     for item in new_processed_data:
    #         if item is not None:
    #             f.write(json.dumps(item) + "\n")

if __name__ == "__main__":
    main()
