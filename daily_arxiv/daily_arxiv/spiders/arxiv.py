import scrapy
import os
import re


class ArxivSpider(scrapy.Spider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        categories = os.environ.get("CATEGORIES", "cs.CV")
        categories = categories.split(",")
        # Save target category list for subsequent verification / Lưu danh sách danh mục mục tiêu để xác minh sau
        self.target_categories = set(map(str.strip, categories))
        self.start_urls = [
            f"https://arxiv.org/list/{cat}/new" for cat in self.target_categories
        ]  # Starting URL (latest papers in Computer Science) / URL bắt đầu (các bài báo mới nhất trong Khoa học máy tính)

    name = "arxiv"  # Spider name / Tên nhện (spider)
    allowed_domains = ["arxiv.org"]  # Allowed domains / Các tên miền được phép

    def parse(self, response):
        # Extract information for each paper / Trích xuất thông tin cho mỗi bài báo
        anchors = []
        for li in response.css("div[id=dlpage] ul li"):
            href = li.css("a::attr(href)").get()
            if href and "item" in href:
                anchors.append(int(href.split("item")[-1]))

        # Iterate through detailed information of each paper / Duyệt qua thông tin chi tiết của từng bài báo
        for paper in response.css("dl dt"):
            paper_anchor = paper.css("a[name^='item']::attr(name)").get()
            if not paper_anchor:
                continue
                
            paper_id = int(paper_anchor.split("item")[-1])
            if anchors and paper_id >= anchors[-1]:
                continue

            # Get paper ID / Lấy ID bài báo
            abstract_link = paper.css("a[title='Abstract']::attr(href)").get()
            if not abstract_link:
                continue
                
            arxiv_id = abstract_link.split("/")[-1]
            
            # Get corresponding paper description part (dd element) / Lấy phần mô tả bài báo tương ứng (phần tử dd)
            paper_dd = paper.xpath("following-sibling::dd[1]")
            if not paper_dd:
                continue
            
            # Extract paper classification information - in subjects section / Trích xuất thông tin phân loại bài báo - trong phần subjects
            subjects_text = paper_dd.css(".list-subjects .primary-subject::text").get()
            if not subjects_text:
                # If main category not found, try other ways to get category / Nếu không tìm thấy danh mục chính, hãy thử các cách khác để lấy danh mục
                subjects_text = paper_dd.css(".list-subjects::text").get()
            
            if subjects_text:
                # Parse classification information, usually in format "Computer Vision and Pattern Recognition (cs.CV)"
                # Phân tích thông tin phân loại, thường ở định dạng "Computer Vision and Pattern Recognition (cs.CV)"
                # Extract category code in parentheses / Trích xuất mã danh mục trong ngoặc đơn
                categories_in_paper = re.findall(r'\(([^)]+)\)', subjects_text)
                
                # Check if paper categories intersect with target categories / Kiểm tra xem danh mục bài báo có giao nhau với danh mục mục tiêu không
                paper_categories = set(categories_in_paper)
                if paper_categories.intersection(self.target_categories):
                    yield {
                        "id": arxiv_id,
                        "categories": list(paper_categories),  # Add category information for debugging / Thêm thông tin danh mục để gỡ lỗi
                    }
                    self.logger.info(f"Found paper {arxiv_id} with categories {paper_categories}")
                else:
                    self.logger.debug(f"Skipped paper {arxiv_id} with categories {paper_categories} (not in target {self.target_categories})")
            else:
                # If classification information cannot be obtained, log warning but still return paper (maintain backward compatibility)
                # Nếu không thể lấy thông tin phân loại, hãy ghi nhật ký cảnh báo nhưng vẫn trả lại bài báo (duy trì khả năng tương thích ngược)
                self.logger.warning(f"Could not extract categories for paper {arxiv_id}, including anyway")
                yield {
                    "id": arxiv_id,
                    "categories": [],
                }
