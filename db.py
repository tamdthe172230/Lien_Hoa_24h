import os
import sqlite3
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
DB_PATH = os.path.join(DB_DIR, 'news.db')

def get_db_connection():
    """Tạo kết nối đến cơ sở dữ liệu SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Khởi tạo cơ sở dữ liệu và bảng cần thiết."""
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tạo bảng lưu trữ bài viết
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            source TEXT NOT NULL,
            publish_date TEXT,
            summary TEXT,
            category TEXT,
            sentiment TEXT,
            content TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Khoi tao co so du lieu thanh cong tai:", DB_PATH)

def insert_article(title, url, source, publish_date=None, summary=None, category=None, sentiment=None, content=None):
    """Chèn một bài viết mới vào CSDL. Trả về True nếu thành công, False nếu đã tồn tại."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO articles (title, url, source, publish_date, summary, category, sentiment, content)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, url, source, publish_date, summary, category, sentiment, content))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Xử lý khi URL đã tồn tại trong database (tránh trùng lặp)
        return False
    finally:
        conn.close()

def get_articles(search_query=None, category=None, source=None, limit=20, offset=0):
    """Lấy danh sách các bài viết kèm theo bộ lọc và tìm kiếm."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM articles WHERE 1=1"
    params = []
    
    if category:
        query += " AND category = ?"
        params.append(category)
        
    if source:
        query += " AND source = ?"
        params.append(source)
        
    if search_query:
        query += " AND (title LIKE ? OR summary LIKE ? OR content LIKE ?)"
        search_val = f"%{search_query}%"
        params.extend([search_val, search_val, search_val])
        
    # Tính tổng số bài báo thỏa mãn điều kiện lọc
    count_query = query.replace("SELECT *", "SELECT COUNT(*)", 1)
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()[0]
    
    # Lấy dữ liệu phân trang, sắp xếp theo ngày đăng thực tế mới nhất
    query += " ORDER BY publish_date DESC, scraped_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    articles = []
    for row in rows:
        articles.append(dict(row))
        
    conn.close()
    return articles, total_count

def get_stats():
    """Thống kê số lượng bài báo theo chuyên mục và nguồn tin."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Thống kê theo chuyên mục (category)
    cursor.execute("SELECT category, COUNT(*) as count FROM articles GROUP BY category")
    categories = {row['category'] or 'Chưa phân loại': row['count'] for row in cursor.fetchall()}
    
    # Thống kê theo nguồn báo (source)
    cursor.execute("SELECT source, COUNT(*) as count FROM articles GROUP BY source")
    sources = {row['source']: row['count'] for row in cursor.fetchall()}
    
    # Tổng số bài báo
    cursor.execute("SELECT COUNT(*) FROM articles")
    total = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total': total,
        'by_category': categories,
        'by_source': sources
    }

# Tự động khởi chạy kiểm tra khi chạy trực tiếp file db.py
if __name__ == '__main__':
    init_db()
