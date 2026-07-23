import os
import google.generativeai as genai
import json
import re

def fallback_processing(title, content):
    """
    Xử lý bài báo dự phòng (khi không có Gemini API Key hoặc gọi API lỗi).
    Tự động tóm tắt và phân loại dựa trên các quy tắc từ khóa cơ bản.
    """
    content = content or ""
    title = title or ""
    
    # 1. Tóm tắt sơ bộ (Lấy 2 câu đầu tiên của nội dung)
    sentences = re.split(r'(?<=[.!?])\s+', content)
    summary_sentences = [s.strip() for s in sentences if s.strip()]
    summary = " ".join(summary_sentences[:2])
    if not summary:
        summary = title
    if len(summary) > 200:
        summary = summary[:197] + "..."

    # 2. Phân loại chuyên mục theo tần suất từ khóa (Scoring Algorithm)
    full_text = (title + " " + content).lower()
    
    category_keywords = {
        "Chính trị - Hành chính": ["chính quyền", "ubnd", "cán bộ", "đảng", "hội nghị", "bí thư", "chủ tịch", "hành chính", "chỉ thị", "bầu cử", "hđnd"],
        "Kinh tế - Đầu tư": ["thủy sản", "doanh nghiệp", "nuôi trồng", "sản xuất", "kinh doanh", "thu nhập", "hộ dân", "hợp tác xã", "tài chính", "thương mại"],
        "Đầu tư - Hạ tầng": ["đê biển", "nâng cấp", "xây dựng", "dự án", "hạ tầng", "giao thông", "tuyến đường", "bê tông", "thi công", "san lấp", "cầu"],
        "Văn hóa - Xã hội": ["lễ hội", "đền tiên công", "tiên công", "văn hóa", "lễ rước", "du lịch", "di tích", "lịch sử", "đình quỳnh biểu", "thượng thọ"],
        "Đời sống dân sinh": ["y tế", "dịch bệnh", "môi trường", "rác thải", "phun thuốc", "sức khỏe", "sinh hoạt", "nghèo", "nhà nhân đạo", "khó khăn", "việc làm"]
    }
    
    scores = {}
    for cat, keywords in category_keywords.items():
        score = sum(1 for kw in keywords if kw in full_text)
        scores[cat] = score
        
    max_cat = "Khác"
    max_score = 0
    for cat, score in scores.items():
        if score > max_score:
            max_score = score
            max_cat = cat
            
    category = max_cat

    # 3. Phân tích sắc thái cơ bản
    sentiment = "Trung lập"
    positive_words = ["thành công", "phát triển", "độc đáo", "đạt hiệu quả", "tin tưởng", "vui mừng", "nâng cao", "tiến bộ"]
    negative_words = ["dịch bệnh", "thiên tai", "bão lũ", "ngập lụt", "vi phạm", "tai nạn", "sạt lở"]
    
    pos_count = sum(1 for w in positive_words if w in full_text)
    neg_count = sum(1 for w in negative_words if w in full_text)
    
    if pos_count > neg_count:
        sentiment = "Tích cực"
    elif neg_count > pos_count:
        sentiment = "Cần lưu ý"

    return {
        "is_relevant": True,
        "summary": summary,
        "category": category,
        "sentiment": sentiment
    }

def process_article_with_gemini(title, content, api_key=None):
    """
    Sử dụng Gemini API để phân tích, tóm tắt và phân loại bài báo.
    """
    if not api_key:
        # Thử lấy từ môi trường nếu không có tham số truyền vào
        api_key = os.environ.get("GEMINI_API_KEY")
        
    if not api_key:
        # Nếu hoàn toàn không có API Key, chuyển sang chế độ dự phòng
        return fallback_processing(title, content)
        
    try:
        # Cấu hình API Key
        genai.configure(api_key=api_key)
        
        # Chọn model phù hợp cho phân tích văn bản tiếng Việt
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Bạn là một trợ lý AI thông minh chuyên xử lý dữ liệu tin tức báo chí.
        Hãy đọc Tiêu đề và Nội dung bài viết dưới đây và phân tích theo các yêu cầu sau:
        
        1. Xác định xem bài viết này có phải nói về Phường Liên Hòa (thuộc thị xã Quảng Yên, tỉnh Quảng Ninh, Việt Nam) hoặc các chủ đề trực tiếp ảnh hưởng đến phường Liên Hòa hay không. Trả về True hoặc False (trường 'is_relevant').
        2. Tạo một bản tóm tắt bài báo bằng Tiếng Việt ngắn gọn từ 2 đến 3 câu (trường 'summary').
        3. Phân loại bài viết vào một trong các chuyên mục sau: "Chính trị - Hành chính", "Kinh tế - Đầu tư", "Đầu tư - Hạ tầng", "Văn hóa - Xã hội", "Đời sống dân sinh", "Khác" (trường 'category').
        4. Phân tích sắc thái bài viết: "Tích cực", "Trung lập", "Cần lưu ý" (trường 'sentiment').
        
        Thông tin bài viết:
        Tiêu đề: {title}
        Nội dung: {content}
        
        Yêu cầu trả về kết quả định dạng JSON duy nhất với cấu trúc sau:
        {{
            "is_relevant": true/false,
            "summary": "nội dung tóm tắt bài báo",
            "category": "tên chuyên mục phù hợp",
            "sentiment": "Tích cực/Trung lập/Cần lưu ý"
        }}
        Không thêm bất kỳ văn bản nào khác ngoài mã JSON sạch này.
        """
        
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        # Parse kết quả JSON
        result = json.loads(response.text.strip())
        return result
        
    except Exception as e:
        print(f"Lỗi khi gọi Gemini API: {e}. Chuyển sang xử lý dự phòng...")
        return fallback_processing(title, content)
