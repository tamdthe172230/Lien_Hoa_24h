import os
import threading
import time
from flask import Flask, jsonify, request, render_template, send_from_directory
from db import init_db, get_articles, get_stats, get_db_connection
from scraper import scrape_and_save_all
from ai_processor import process_article_with_gemini

app = Flask(__name__, template_folder='templates', static_folder='static')

# Khóa luồng (Lock) để tránh nhiều tiến trình cào tin chạy song song
scrape_lock = threading.Lock()
is_scraping = False

def run_background_scraper():
    """Hàm chạy ngầm cào tin định kỳ (cứ mỗi 1 tiếng/lần)."""
    global is_scraping
    print("Khoi dong tien trinh cao tin tu dong dinh ky...")
    # Cào tin lần đầu khi khởi động
    with scrape_lock:
        is_scraping = True
        try:
            scrape_and_save_all()
            enrich_articles_with_ai()
        except Exception as e:
            print(f"Loi cao tin nen: {e}")
        finally:
            is_scraping = False
            
    while True:
        # Chờ 1 tiếng (3600 giây)
        time.sleep(3600)
        with scrape_lock:
            is_scraping = True
            try:
                print("Dang cao du lieu dinh ky tu dong...")
                scrape_and_save_all()
                enrich_articles_with_ai()
            except Exception as e:
                print(f"Loi cao tin dinh ky: {e}")
            finally:
                is_scraping = False

def enrich_articles_with_ai(api_key=None):
    """Quét các bài viết chưa phân loại trong DB và chạy xử lý AI."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, content 
        FROM articles 
        WHERE category = 'Chưa phân loại' OR summary = '' OR summary IS NULL OR sentiment = 'Trung lập'
    """)
    rows = cursor.fetchall()
    
    updated_count = 0
    for row in rows:
        art_id = row['id']
        title = row['title']
        content = row['content']
        
        # Chạy phân tích AI
        ai_res = process_article_with_gemini(title, content, api_key)
        
        # Cập nhật kết quả vào DB
        cursor.execute("""
            UPDATE articles 
            SET summary = ?, category = ?, sentiment = ?
            WHERE id = ?
        """, (ai_res['summary'], ai_res['category'], ai_res['sentiment'], art_id))
        updated_count += 1
        
    conn.commit()
    conn.close()
    print(f"Da cap nhat AI cho {updated_count} bai viet.")
    return updated_count

@app.route('/')
def home():
    """Render giao diện chính."""
    return render_template('index.html')

@app.route('/api/news', methods=['GET'])
def api_get_news():
    """API lấy danh sách bài viết kèm bộ lọc, tìm kiếm và phân trang."""
    search_query = request.args.get('q', '')
    category = request.args.get('category', '')
    source = request.args.get('source', '')
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    
    offset = (page - 1) * limit
    
    articles, total_count = get_articles(
        search_query=search_query,
        category=category,
        source=source,
        limit=limit,
        offset=offset
    )
    
    return jsonify({
        'status': 'success',
        'data': articles,
        'pagination': {
            'page': page,
            'limit': limit,
            'total_count': total_count,
            'total_pages': (total_count + limit - 1) // limit
        }
    })

@app.route('/api/scrape', methods=['POST'])
def api_trigger_scrape():
    """Kích hoạt cào tin tức và phân tích AI tức thời."""
    global is_scraping
    if is_scraping:
        return jsonify({
            'status': 'error',
            'message': 'Tiến trình cào dữ liệu đang bận chạy ngầm, vui lòng đợi.'
        }), 409
        
    data = request.json or {}
    api_key = data.get('api_key', '')
    
    def process_scrape():
        global is_scraping
        with scrape_lock:
            is_scraping = True
            try:
                # 1. Cào tin mới
                new_count = scrape_and_save_all()
                # 2. Xử lý AI cho các tin chưa phân loại
                enrich_count = enrich_articles_with_ai(api_key)
                print(f"Cao thu cong thanh cong. Tin moi: {new_count}, Da cap nhat AI: {enrich_count}")
            except Exception as e:
                print(f"Loi khi cao thu cong: {e}")
            finally:
                is_scraping = False

    # Chạy bất đồng bộ để tránh bị timeout trên HTTP response
    threading.Thread(target=process_scrape).start()
    
    return jsonify({
        'status': 'success',
        'message': 'Đã kích hoạt tiến trình cào dữ liệu mới và phân tích AI thành công.'
    })

@app.route('/api/stats', methods=['GET'])
def api_get_stats():
    """API thống kê số lượng bài báo."""
    try:
        stats = get_stats()
        return jsonify({
            'status': 'success',
            'data': stats
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/status', methods=['GET'])
def api_get_status():
    """Kiểm tra xem hệ thống cào tin có đang bận không."""
    return jsonify({
        'status': 'success',
        'is_scraping': is_scraping
    })

# Khởi tạo Database và chạy Thread cào tin ngầm trực tiếp khi khởi động ứng dụng (giúp hoạt động trên Gunicorn/Render)
init_db()

t = threading.Thread(target=run_background_scraper, daemon=True)
t.start()

if __name__ == '__main__':
    # Khởi chạy Flask Server cục bộ
    port = int(os.environ.get('PORT', 5000))
    print(f"Khoi dong may chu web tai http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)
