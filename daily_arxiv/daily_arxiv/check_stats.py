#!/usr/bin/env python3
"""
Script to check Scrapy crawling statistics / Kịch bản kiểm tra số liệu thống kê thu thập thông tin của Scrapy
Used to get deduplication check status results / Được sử dụng để lấy kết quả trạng thái kiểm tra loại bỏ trùng lặp

Features / Các tính năng:
- Check duplication between today's and yesterday's paper data / Kiểm tra sự trùng lặp giữa dữ liệu bài báo hôm nay và hôm qua
- Remove duplicate papers, keep new content / Loại bỏ các mục bài báo trùng lặp, giữ lại nội dung mới
- Decide workflow continuation based on deduplication results / Quyết định tiếp tục quy trình làm việc dựa trên kết quả loại bỏ trùng lặp
"""
import json
import sys
import os
from datetime import datetime, timedelta

def load_papers_data(file_path):
    """
    Load complete paper data from jsonl file
    Tải dữ liệu bài báo hoàn chỉnh từ tệp jsonl
    
    Args:
        file_path (str): JSONL file path / Đường dẫn tập tin JSONL
        
    Returns:
        list: List of paper data / Danh sách dữ liệu bài báo
        set: Set of paper IDs / Tập hợp ID bài báo
    """
    if not os.path.exists(file_path):
        return [], set()
    
    papers = []
    ids = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    papers.append(data)
                    ids.add(data.get('id', ''))
        return papers, ids
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return [], set()

def save_papers_data(papers, file_path):
    """
    Save paper data to jsonl file
    Lưu dữ liệu bài báo vào tệp jsonl
    
    Args:
        papers (list): List of paper data / Danh sách dữ liệu bài báo
        file_path (str): File path / Đường dẫn tập tin
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            for paper in papers:
                f.write(json.dumps(paper, ensure_ascii=False) + '\n')
        return True
    except Exception as e:
        print(f"Error saving {file_path}: {e}", file=sys.stderr)
        return False

def perform_deduplication():
    """
    Perform deduplication over multiple past days
    Thực hiện loại bỏ trùng lặp trong nhiều ngày qua: xóa các mục bài báo trùng lặp với lịch sử nhiều ngày, giữ lại nội dung mới
    
    Returns:
        str: Deduplication status / Trạng thái loại bỏ trùng lặp
             - "has_new_content": Has new content / Có nội dung mới
             - "no_new_content": No new content / Không có nội dung mới
             - "no_data": No data / Không có dữ liệu
             - "error": Processing error / Lỗi xử lý
    """

    today = datetime.now().strftime("%Y-%m-%d")
    today_file = f"../data/{today}.jsonl"
    history_days = 7  # Compare data from past few days / So sánh dữ liệu từ vài ngày trước

    if not os.path.exists(today_file):
        print("Today's data file does not exist / Tệp dữ liệu hôm nay không tồn tại", file=sys.stderr)
        return "no_data"

    try:
        today_papers, today_ids = load_papers_data(today_file)
        print(f"Today's total papers: {len(today_papers)} / Tổng số bài báo hôm nay: {len(today_papers)}", file=sys.stderr)

        if not today_papers:
            return "no_data"

        # Collect historical multi-day ID set / Thu thập tập hợp ID lịch sử nhiều ngày
        history_ids = set()
        for i in range(1, history_days + 1):
            date_str = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            history_file = f"../data/{date_str}.jsonl"
            _, past_ids = load_papers_data(history_file)
            history_ids.update(past_ids)

        print(f"History {history_days} days deduplication library size: {len(history_ids)} / Kích thước thư viện loại bỏ trùng lặp lịch sử {history_days} ngày: {len(history_ids)}", file=sys.stderr)

        duplicate_ids = today_ids & history_ids

        if duplicate_ids:
            print(f"Found {len(duplicate_ids)} historical duplicate papers / Đã tìm thấy {len(duplicate_ids)} bài báo trùng lặp lịch sử", file=sys.stderr)
            new_papers = [paper for paper in today_papers if paper.get('id', '') not in duplicate_ids]

            print(f"Remaining papers after deduplication: {len(new_papers)} / Số bài báo còn lại sau khi loại bỏ trùng lặp: {len(new_papers)}", file=sys.stderr)

            if new_papers:
                if save_papers_data(new_papers, today_file):
                    print(f"Today's file updated, removed {len(duplicate_ids)} duplicate papers / Đã cập nhật tệp hôm nay, đã xóa {len(duplicate_ids)} bài báo trùng lặp", file=sys.stderr)
                    return "has_new_content"
                else:
                    print("Failed to save deduplicated data / Lưu dữ liệu sau khi loại bỏ trùng lặp thất bại", file=sys.stderr)
                    return "error"
            else:
                try:
                    os.remove(today_file)
                    print("All papers are duplicate content, today's file deleted / Tất cả nội dung đều là trùng lặp, tệp hôm nay đã bị xóa", file=sys.stderr)
                except Exception as e:
                    print(f"Failed to delete file: {e} / Lỗi khi xóa tệp: {e}", file=sys.stderr)
                return "no_new_content"
        else:
            print("All content is new / Tất cả nội dung đều là mới", file=sys.stderr)
            return "has_new_content"

    except Exception as e:
        print(f"Deduplication processing failed: {e} / Quá trình loại bỏ trùng lặp thất bại: {e}", file=sys.stderr)
        return "error"

def main():
    """
    Check deduplication status and return corresponding exit code
    Kiểm tra trạng thái loại bỏ trùng lặp và trả về mã thoát tương ứng
    
    Exit code meanings / Ý nghĩa mã thoát:
    0: Has new content, continue processing / Có nội dung mới, tiếp tục xử lý
    1: No new content, stop workflow / Không có nội dung mới, dừng quy trình làm việc
    2: Processing error / Lỗi xử lý
    """
    
    print("Performing intelligent deduplication check... / Đang thực hiện kiểm tra loại bỏ trùng lặp thông minh...", file=sys.stderr)
    
    # Perform deduplication processing / Thực hiện quy trình loại bỏ trùng lặp
    dedup_status = perform_deduplication()
    
    if dedup_status == "has_new_content":
        print("✅ Deduplication completed, new content found, continue workflow / Đã hoàn thành loại bỏ trùng lặp, tìm thấy nội dung mới, tiếp tục quy trình làm việc", file=sys.stderr)
        sys.exit(0)
    elif dedup_status == "no_new_content":
        print("⏹️ Deduplication completed, no new content, stop workflow / Đã hoàn thành loại bỏ trùng lặp, không có nội dung mới, dừng quy trình làm việc", file=sys.stderr)
        sys.exit(1)
    elif dedup_status == "no_data":
        print("⏹️ No data today, stop workflow / Hôm nay không có dữ liệu, dừng quy trình làm việc", file=sys.stderr)
        sys.exit(1)
    elif dedup_status == "error":
        print("❌ Deduplication processing error, stop workflow / Lỗi xử lý loại bỏ trùng lặp, dừng quy trình làm việc", file=sys.stderr)
        sys.exit(2)
    else:
        # Unexpected case: unknown status / Tình huống bất ngờ: trạng thái không xác định
        print("❌ Unknown deduplication status, stop workflow / Trạng thái loại bỏ trùng lặp không xác định, dừng quy trình làm việc", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main() 