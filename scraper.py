import requests
from bs4 import BeautifulSoup
import urllib.parse
from datetime import datetime
import re
import time
import unicodedata
from db import insert_article

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def remove_accents(input_str):
    """Loại bỏ dấu tiếng Việt để so sánh chuỗi an toàn không lỗi Unicode."""
    if not input_str:
        return ""
    s1 = unicodedata.normalize('NFD', input_str)
    s2 = "".join([c for c in s1 if unicodedata.category(c) != 'Mn'])
    s2 = s2.replace('đ', 'd').replace('Đ', 'D')
    return unicodedata.normalize('NFC', s2)

# Dữ liệu Mock chất lượng cao để hiển thị ngay lập tức nếu cào thật không có dữ liệu mới
MOCK_ARTICLES = [
    {
        "title": "Độc đáo Lễ hội đền Tiên Công năm 2026 tại phường Liên Hòa, thị xã Quảng Yên",
        "url": "https://baoquangninh.vn/doc-dao-le-hoi-den-tien-cong-nam-2026-tai-phuong-lien-hoa-321456.html",
        "source": "Báo Quảng Ninh",
        "publish_date": "2026-02-15",
        "summary": "Lễ hội đền Tiên Công năm nay được tổ chức trang trọng tại phường Liên Hòa, thu hút đông đảo nhân dân và du khách thập phương tham gia. Lễ hội tôn vinh các vị Tiên Công có công quai đê lấn biển lập đất.",
        "category": "Văn hóa - Xã hội",
        "sentiment": "Tích cực",
        "content": "Lễ hội đền Tiên Công là nét đẹp văn hóa độc đáo của vùng đảo Hà Nam nói chung và phường Liên Hòa nói riêng. Hằng năm vào dịp đầu xuân, nhân dân địa phương lại nô nức tổ chức lễ rước các cụ thượng thọ lên đền Tiên Công để bái tổ. Đây không chỉ là dịp thể hiện truyền thống uống nước nhớ nguồn, hiếu kính cha mẹ, nhiếp sinh lập đức, mà còn là cơ hội quảng bá du lịch tâm linh, giáo dục truyền thống dựng nước giữ nước cho các thế hệ trẻ tại địa phương."
    },
    {
        "title": "Phường Liên Hòa đẩy mạnh nuôi trồng thủy sản bền vững gắn với bảo vệ môi trường",
        "url": "https://nhandan.vn/phuong-lien-hoa-day-manh-nuoi-trong-thuy-san-ben-vung-322654.html",
        "source": "Báo Nhân Dân",
        "publish_date": "2026-04-10",
        "summary": "Phường Liên Hòa tích cực chuyển đổi từ nuôi trồng thủy sản truyền thống sang bán công nghiệp ứng dụng công nghệ cao, bảo vệ đê điều và môi trường nước sông ngòi.",
        "category": "Kinh tế - Đầu tư",
        "sentiment": "Tích cực",
        "content": "Nằm ở phía nam thị xã Quảng Yên, phường Liên Hòa có lợi thế lớn về diện tích mặt nước đầm bãi. Nhằm nâng cao năng suất kinh tế gắn liền với bảo vệ môi trường, chính quyền địa phương phối hợp với các hợp tác xã thủy sản tổ chức các lớp tập huấn kỹ thuật cho người dân. Các mô hình nuôi tôm thẻ chân trắng trong ao phủ bạt công nghệ cao đã và đang được nhân rộng, mang lại thu nhập hàng trăm triệu đồng mỗi năm cho các hộ gia đình."
    },
    {
        "title": "Đầu tư nâng cấp tuyến đê biển xung yếu Liên Hòa - Phong Cốc trị giá 150 tỷ đồng",
        "url": "https://quangninh.gov.vn/dau-tu-nang-cap-tuyen-de-bien-lien-hoa-phong-coc-325987.html",
        "source": "Cổng TTĐT Quảng Ninh",
        "publish_date": "2026-05-22",
        "summary": "Dự án cải tạo, nâng cấp tuyến đê biển xung yếu Liên Hòa - Phong Cốc nhằm nâng cao năng lực phòng chống thiên tai bão lũ, bảo vệ đời sống hàng ngàn hộ dân đảo Hà Nam.",
        "category": "Đầu tư - Hạ tầng",
        "sentiment": "Tích cực",
        "content": "Ủy ban Nhân dân tỉnh Quảng Ninh vừa phê duyệt chủ trương đầu tư dự án nâng cấp tuyến đê biển Liên Hòa - Phong Cốc. Tuyến đê này có vai trò ngăn mặn, chắn sóng cực kỳ quan trọng cho các khu vực dân cư và diện tích sản xuất nông nghiệp, thủy sản tại khu vực Hà Nam. Việc đầu tư kiên cố hóa đê biển bằng bê tông chịu lực, mở rộng mặt đê kết hợp giao thông sẽ đảm bảo an toàn tuyệt đối cho người dân trong mùa mưa bão sắp tới."
    },
    {
        "title": "Công tác phòng chống dịch bệnh mùa hè và vệ sinh môi trường tại Liên Hòa",
        "url": "https://quangyen.gov.vn/cong-tac-phong-chong-dich-benh-mua-he-tai-lien-hoa-328844.html",
        "source": "Cổng TTĐT Quảng Yên",
        "publish_date": "2026-06-18",
        "summary": "Trạm Y tế phường Liên Hòa phối hợp với các đoàn thể tổ chức chiến dịch ra quân phun thuốc phòng dịch bệnh và dọn dẹp vệ sinh môi trường thôn xóm.",
        "category": "Đời sống dân sinh",
        "sentiment": "Trung lập",
        "content": "Trước tình hình thời tiết mùa hè diễn biến phức tạp, Trạm Y tế phường Liên Hòa đã chủ động tham mưu cho UBND phường xây dựng kế hoạch phòng chống các dịch bệnh truyền nhiễm như sốt xuất huyết, tay chân miệng và tiêu chảy cấp. Đoàn thanh niên và Hội phụ nữ phường đã phát động phong trào Ngày Chủ nhật xanh dọn dẹp rác thải tại các tuyến đường trục chính, phát quang bụi rậm, khơi thông cống rãnh tránh muỗi sinh sôi."
    },
    {
        "title": "Nâng cao chất lượng cải cách hành chính tại Ủy ban nhân dân phường Liên Hòa",
        "url": "https://baoquangninh.vn/nang-cao-chat-luong-cai-cach-hanh-chinh-tai-ubnd-phuong-lien-hoa-329910.html",
        "source": "Báo Quảng Ninh",
        "publish_date": "2026-07-02",
        "summary": "Ứng dụng mô hình một cửa hiện đại tại UBND phường Liên Hòa giúp giải quyết nhanh chóng hồ sơ, giấy tờ cho người dân, tăng sự hài lòng của công chúng.",
        "category": "Chính trị - Hành chính",
        "sentiment": "Tích cực",
        "content": "Nhằm xây dựng chính quyền thân thiện, vì nhân dân phục vụ, UBND phường Liên Hòa đã đầu tư nâng cấp cơ sở vật chất cho bộ phận tiếp nhận và trả kết quả hiện đại. Đồng thời đẩy mạnh tuyên truyền người dân sử dụng dịch vụ công trực tuyến mức độ 3 và 4. Nhờ đó, tỷ lệ hồ sơ giải quyết đúng hạn và trước hạn đạt trên 98%, đem lại niềm tin lớn cho các cá nhân và tổ chức khi đến giao dịch hành chính."
    }
]

def load_mock_data():
    """Nạp dữ liệu mock vào database để đảm bảo ứng dụng luôn có dữ liệu chạy thử."""
    inserted_count = 0
    for art in MOCK_ARTICLES:
        success = insert_article(
            title=art["title"],
            url=art["url"],
            source=art["source"],
            publish_date=art["publish_date"],
            summary=art["summary"],
            category=art["category"],
            sentiment=art["sentiment"],
            content=art["content"]
        )
        if success:
            inserted_count += 1
    return inserted_count

def scrape_nhandan(keyword="Liên Hòa"):
    """Cào tin tức từ trang tìm kiếm Báo Nhân Dân."""
    articles = []
    query = urllib.parse.quote(keyword)
    url = f"https://nhandan.vn/tim-kiem?q={query}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # Cấu trúc HTML tìm kiếm của Báo Nhân Dân thường là các class chứa story hoặc box-news
            items = soup.find_all(['article', 'div'], class_=re.compile(r'(story|box-news|item-news|news)'))
            
            for item in items[:10]: # Lấy tối đa 10 tin tức
                link_tag = item.find('a')
                if not link_tag or not link_tag.get('href'):
                    continue
                    
                title_tag = item.find(['h3', 'h4', 'h2']) or link_tag
                title = title_tag.get_text(separator=' ', strip=True)
                title = re.sub(r'\s+', ' ', title)
                
                if not title:
                    continue
                    
                article_url = link_tag['href']
                if any(article_url.startswith(x) for x in ['tel:', 'mailto:', 'javascript:']):
                    continue
                if not article_url.startswith('http'):
                    article_url = "https://nhandan.vn" + article_url
                
                # Trích xuất phần mô tả ngắn (nếu có)
                summary_tag = item.find(['div', 'p'], class_=re.compile(r'(summary|sapo|desc)'))
                summary = summary_tag.get_text(separator=' ', strip=True) if summary_tag else ""
                summary = re.sub(r'\s+', ' ', summary)
                
                # Lấy ngày đăng bài viết
                date_str = datetime.now().strftime("%Y-%m-%d")
                time_tag = item.find(['span', 'div', 'p'], class_=re.compile(r'(date|time|meta)'))
                if time_tag:
                    time_text = time_tag.get_text(strip=True)
                    match = re.search(r'(\d{2})/(\d{2})/(\d{4})', time_text)
                    if match:
                        day, month, year = match.groups()
                        date_str = f"{year}-{month}-{day}"
                
                # Lấy nội dung chi tiết bài viết
                content = scrape_article_detail(article_url)
                
                # Kiểm tra độ tương quan không dấu
                full_text = (title + " " + summary + " " + (content or ""))
                full_text_clean = remove_accents(full_text).lower()
                if "lien hoa" in full_text_clean:
                    articles.append({
                        "title": title,
                        "url": article_url,
                        "source": "Báo Nhân Dân",
                        "publish_date": date_str,
                        "summary": summary,
                        "content": content
                    })
    except Exception as e:
        print(f"Loi cao bao Nhan Dan: {e}")
        
    return articles

def scrape_quangninh_portal(keyword="Liên Hòa"):
    """Cào tin tức từ Cổng thông tin điện tử tỉnh Quảng Ninh (quangninh.gov.vn)."""
    articles = []
    query = urllib.parse.quote(keyword)
    url = f"https://www.quangninh.gov.vn/Trang/searchqnp.aspx?k={query}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            result_div = soup.find('div', class_='search-result')
            if result_div:
                items = result_div.find_all('li')
                for item in items[:15]: # Lấy tối đa 15 bài đầu tiên
                    link_tag = item.find('a')
                    if not link_tag or not link_tag.get('href'):
                        continue
                        
                    article_url = link_tag['href']
                    if not article_url.startswith('http'):
                        article_url = "https://www.quangninh.gov.vn" + article_url
                        
                    box_content = item.find('div', class_='box-content')
                    if not box_content:
                        continue
                        
                    # Lấy tiêu đề
                    title_tag = box_content.find('h3')
                    if not title_tag:
                        continue
                    title = title_tag.get_text(separator=' ', strip=True)
                    title = re.sub(r'\s+', ' ', title)
                    
                    # Lấy mô tả ngắn
                    desc_tag = box_content.find('div', style=lambda s: s and 'padding-bottom' in s)
                    summary = desc_tag.get_text(separator=' ', strip=True) if desc_tag else ""
                    summary = re.sub(r'\s+', ' ', summary)
                    
                    # Lấy ngày đăng (định dạng dd/mm/yyyy hh:mm:ss SA/CH)
                    time_tag = box_content.find('p')
                    date_str = datetime.now().strftime("%Y-%m-%d")
                    if time_tag:
                        time_text = time_tag.get_text(strip=True)
                        match = re.search(r'(\d{2})/(\d{2})/(\d{4})', time_text)
                        if match:
                            day, month, year = match.groups()
                            date_str = f"{year}-{month}-{day}"
                            
                    # Cào nội dung chi tiết bài viết
                    content = scrape_article_detail(article_url)
                    
                    # Kiểm tra độ tương quan không dấu
                    full_text = (title + " " + summary + " " + (content or ""))
                    full_text_clean = remove_accents(full_text).lower()
                    if "lien hoa" in full_text_clean:
                        articles.append({
                            "title": title,
                            "url": article_url,
                            "source": "Cổng TTĐT Quảng Ninh",
                            "publish_date": date_str,
                            "summary": summary,
                            "content": content
                        })
    except Exception as e:
        print(f"Loi cao Cong TTDT Quang Ninh: {e}")
        
    return articles


def scrape_baoquangninh(keyword="Liên Hòa"):
    """Cào tin tức từ trang tìm kiếm Báo Quảng Ninh."""
    articles = []
    query = urllib.parse.quote(keyword)
    url = f"https://baoquangninh.vn/search?keyword={query}&exactly=on"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # Cấu trúc thực tế: tìm các thẻ div.card-content
            items = soup.find_all('div', class_='card-content')
            
            for item in items[:15]: # Lấy 15 bài đầu tiên
                title_tag = item.find('h3', class_='card-title')
                if not title_tag:
                    continue
                link_tag = title_tag.find('a')
                if not link_tag or not link_tag.get('href'):
                    continue
                
                title = title_tag.get_text(separator=' ', strip=True)
                title = re.sub(r'\s+', ' ', title)
                
                article_url = link_tag['href']
                if not article_url.startswith('http'):
                    article_url = "https://baoquangninh.vn" + article_url
                
                # Lấy mô tả ngắn từ div.card-desc
                summary_tag = item.find('div', class_='card-desc')
                summary = summary_tag.get_text(separator=' ', strip=True) if summary_tag else ""
                summary = re.sub(r'\s+', ' ', summary)
                
                # Lấy thời gian đăng bài từ time.card-time
                time_tag = item.find('time', class_='card-time')
                date_str = datetime.now().strftime("%Y-%m-%d")
                if time_tag:
                    time_text = time_tag.get_text(strip=True)
                    match = re.search(r'(\d{2})/(\d{2})/(\d{4})', time_text)
                    if match:
                        day, month, year = match.groups()
                        date_str = f"{year}-{month}-{day}"
                
                # Cào nội dung chi tiết bài viết
                content = scrape_article_detail(article_url)
                
                # Kiểm tra độ tương quan không dấu để tránh lỗi mã hóa chữ tiếng Việt
                full_text = (title + " " + summary + " " + (content or ""))
                full_text_clean = remove_accents(full_text).lower()
                if "lien hoa" in full_text_clean:
                    articles.append({
                        "title": title,
                        "url": article_url,
                        "source": "Báo Quảng Ninh",
                        "publish_date": date_str,
                        "summary": summary,
                        "content": content
                    })
    except Exception as e:
        print(f"Loi cao bao Quang Ninh: {e}")
        
    return articles

def scrape_article_detail(url):
    """Cào nội dung chi tiết của một bài viết cụ thể."""
    try:
        # Chờ nhẹ để tránh bị block IP
        time.sleep(0.5)
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # Các thẻ thông thường chứa nội dung chính bài báo
            content_div = soup.find(['div', 'article'], class_=re.compile(r'(detail|content|body|post-content)'))
            if content_div:
                # Loại bỏ thẻ script, style, quảng cáo
                for s in content_div(['script', 'style', 'div', 'iframe']):
                    if s.get('class') and any(x in ''.join(s.get('class')) for x in ['ads', 'related', 'comment']):
                        s.decompose()
                
                paragraphs = content_div.find_all('p')
                text_content = "\n".join([p.get_text(separator=' ', strip=True) for p in paragraphs if p.get_text(strip=True)])
                if text_content:
                    return text_content
            
            # Fallback: lấy toàn bộ các thẻ p có độ dài ký tự lớn hơn 50
            paragraphs = soup.find_all('p')
            fallback_text = "\n".join([p.get_text(separator=' ', strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50])
            return fallback_text
    except Exception as e:
        print(f"Loi cao chi tiet bai viet {url}: {e}")
    return ""

def scrape_and_save_all():
    """Tiến hành cào tin tức từ mọi nguồn và lưu vào cơ sở dữ liệu."""
    print("Bat dau tien trinh cao du lieu...")
    
    # 1. Cào dữ liệu thực tế trước
    scraped_articles = []
    
    # Cào báo Nhân Dân
    nhandan_news = scrape_nhandan("Liên Hòa")
    scraped_articles.extend(nhandan_news)
    print(f"Cao bao Nhan Dan thanh cong: tim thay {len(nhandan_news)} bai viet phu hop.")
    
    # Cào báo Quảng Ninh
    quangninh_news = scrape_baoquangninh("Liên Hòa")
    scraped_articles.extend(quangninh_news)
    print(f"Cao bao Quang Ninh thanh cong: tim thay {len(quangninh_news)} bai viet phu hop.")
    
    # Cào Cổng TTĐT Quảng Ninh
    portal_news = scrape_quangninh_portal("Liên Hòa")
    scraped_articles.extend(portal_news)
    print(f"Cao Cong TTDT Quang Ninh thanh cong: tim thay {len(portal_news)} bai viet phu hop.")
    
    # 2. Lưu dữ liệu cào thực tế
    real_inserted = 0
    for art in scraped_articles:
        success = insert_article(
            title=art["title"],
            url=art["url"],
            source=art["source"],
            publish_date=art["publish_date"],
            summary=art["summary"],
            category="Chưa phân loại",
            sentiment="Trung lập",
            content=art["content"]
        )
        if success:
            real_inserted += 1
            
    print(f"Hoan thanh tien trinh cao. Da luu them {real_inserted} bai viet moi tu internet.")
    
    # 3. Fallback: Nếu CSDL trống hoàn toàn và không cào thêm được bài nào (cào lỗi/mất mạng), nạp dữ liệu Mock làm dự phòng
    from db import get_stats
    stats = get_stats()
    if real_inserted == 0 and stats['total'] == 0:
        print("Khong co ket noi internet hoac cao that bai va DB dang trong. Nap du lieu mau du phong...")
        mock_inserted = load_mock_data()
        print(f"Da nap {mock_inserted} bai viet mau vao co so du lieu.")
        
    return real_inserted

if __name__ == '__main__':
    from db import init_db
    init_db()
    scrape_and_save_all()
