document.addEventListener('DOMContentLoaded', () => {
    // Trạng thái ứng dụng
    let currentPage = 1;
    let currentCategory = '';
    let currentSource = '';
    let searchQuery = '';
    let totalPages = 1;
    let isScrapingActive = false;

    // Các thành phần giao diện
    const articlesContainer = document.getElementById('articles-container');
    const categoryList = document.getElementById('category-list');
    const sourceList = document.getElementById('source-list');
    const searchInput = document.getElementById('search-input');
    const btnScrape = document.getElementById('btn-scrape');
    const btnPrevPage = document.getElementById('btn-prev-page');
    const btnNextPage = document.getElementById('btn-next-page');
    const pageInfo = document.getElementById('page-info');
    const geminiKeyInput = document.getElementById('gemini-key');
    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingText = document.getElementById('loading-text');

    // Thống kê
    const statTotal = document.getElementById('stat-total');
    const statTopCategory = document.getElementById('stat-top-category');
    const statTopCount = document.getElementById('stat-top-count');
    const chartContainer = document.getElementById('chart-container');
    const timelineContainer = document.getElementById('timeline-container');

    // 1. Quản lý Gemini API Key
    const savedKey = localStorage.getItem('gemini_api_key');
    if (savedKey) {
        geminiKeyInput.value = savedKey;
    }

    geminiKeyInput.addEventListener('input', (e) => {
        localStorage.setItem('gemini_api_key', e.target.value.trim());
    });

    // 2. Tải và hiển thị tin tức
    async function loadNews() {
        try {
            const url = new URL('/api/news', window.location.origin);
            url.searchParams.append('page', currentPage);
            url.searchParams.append('limit', 5); // Hiển thị 5 tin mỗi trang cho thoáng
            if (currentCategory) url.searchParams.append('category', currentCategory);
            if (currentSource) url.searchParams.append('source', currentSource);
            if (searchQuery) url.searchParams.append('q', searchQuery);

            const response = await fetch(url);
            const resData = await response.json();

            if (resData.status === 'success') {
                renderArticles(resData.data);
                renderPagination(resData.pagination);
            }
        } catch (error) {
            console.error('Lỗi khi tải tin tức:', error);
            articlesContainer.innerHTML = `<div style="text-align: center; color: var(--accent-rose); padding: 2rem;">Không thể kết nối đến máy chủ. Hãy đảm bảo backend đang chạy.</div>`;
        }
    }

    function renderArticles(articles) {
        if (!articles || articles.length === 0) {
            articlesContainer.innerHTML = `
                <div style="text-align: center; color: var(--text-muted); padding: 4rem 2rem; background: var(--bg-glass); border-radius: 18px; border: 1px dashed var(--border-glass);">
                    🔍 Không tìm thấy bài viết nào phù hợp với bộ lọc hiện tại.
                </div>`;
            return;
        }

        articlesContainer.innerHTML = articles.map(art => {
            // Định dạng ngày đăng
            let dateStr = 'Chưa rõ ngày';
            if (art.publish_date) {
                try {
                    const date = new Date(art.publish_date);
                    dateStr = date.toLocaleDateString('vi-VN', { year: 'numeric', month: 'long', day: 'numeric' });
                } catch {
                    dateStr = art.publish_date;
                }
            }

            // CSS class cho sắc thái sentiment
            const sentimentClass = 'sentiment-' + (art.sentiment || 'trung-lap').toLowerCase().replace(/\s+/g, '-');
            const summaryText = art.summary || 'Không có tóm tắt. Vui lòng bấm cập nhật AI để tạo tóm tắt mới.';

            return `
                <article class="article-card">
                    <div class="article-meta">
                        <span class="badge badge-source">${art.source}</span>
                        <span class="badge badge-category">${art.category || 'Chưa phân loại'}</span>
                        <span class="badge badge-sentiment ${sentimentClass}">${art.sentiment || 'Trung lập'}</span>
                        <span class="date-text">📅 ${dateStr}</span>
                    </div>
                    <a href="${art.url}" target="_blank" class="article-title">${art.title}</a>
                    <div class="article-summary">
                        💡 <strong>Tóm tắt AI:</strong> ${summaryText}
                    </div>
                    <div class="article-actions">
                        <a href="${art.url}" target="_blank" class="btn-read-more">Đọc tin gốc tại nguồn ↗</a>
                    </div>
                </article>
            `;
        }).join('');
    }

    function renderPagination(pagination) {
        currentPage = pagination.page;
        totalPages = pagination.total_pages;

        pageInfo.textContent = `Trang ${currentPage} / ${totalPages || 1}`;
        btnPrevPage.disabled = currentPage <= 1;
        btnNextPage.disabled = currentPage >= totalPages;
    }

    // 3. Tải và hiển thị thống kê
    async function loadStats() {
        try {
            const response = await fetch('/api/stats');
            const resData = await response.json();

            if (resData.status === 'success') {
                const stats = resData.data;

                // Cập nhật thẻ giá trị
                statTotal.textContent = stats.total || 0;

                // Tìm chuyên mục nổi bật nhất
                let topCategory = 'Chưa rõ';
                let topCount = 0;
                for (const [cat, count] of Object.entries(stats.by_category)) {
                    if (count > topCount && cat !== 'Chưa phân loại' && cat !== 'Khác') {
                        topCount = count;
                        topCategory = cat;
                    }
                }
                statTopCategory.textContent = topCategory;
                statTopCount.textContent = `${topCount} bài viết`;

                // Cập nhật biểu đồ cột
                renderStatsChart(stats.by_category, stats.total);
            }
        } catch (error) {
            console.error('Lỗi khi tải thống kê:', error);
        }
    }

    function renderStatsChart(byCategory, total) {
        if (!byCategory || total === 0) {
            chartContainer.innerHTML = `<p style="color: var(--text-muted); font-size: 0.9rem;">Chưa có dữ liệu thống kê chủ đề.</p>`;
            return;
        }

        const categories = [
            'Chính trị - Hành chính',
            'Kinh tế - Đầu tư',
            'Đầu tư - Hạ tầng',
            'Văn hóa - Xã hội',
            'Đời sống dân sinh',
            'Khác'
        ];

        chartContainer.innerHTML = categories.map(cat => {
            const count = byCategory[cat] || 0;
            const percentage = total > 0 ? Math.round((count / total) * 100) : 0;
            return `
                <div class="chart-bar-container">
                    <div class="chart-label-row">
                        <span>${cat}</span>
                        <span>${count} bài (${percentage}%)</span>
                    </div>
                    <div class="chart-bar-bg">
                        <div class="chart-bar-fill" style="width: ${percentage}%"></div>
                    </div>
                </div>
            `;
        }).join('');
    }

    // 4. Tải dòng thời gian sự kiện (Timeline)
    async function loadTimeline() {
        try {
            // Lấy 4 tin tức mới nhất không phân biệt lọc
            const url = new URL('/api/news', window.location.origin);
            url.searchParams.append('limit', 4);
            const response = await fetch(url);
            const resData = await response.json();

            if (resData.status === 'success' && resData.data) {
                const articles = resData.data;
                if (articles.length === 0) {
                    timelineContainer.innerHTML = `<p style="color: var(--text-muted); font-size: 0.85rem;">Chưa có sự kiện nổi bật.</p>`;
                    return;
                }

                timelineContainer.innerHTML = articles.map(art => {
                    let timeText = 'Mới cập nhật';
                    if (art.publish_date) {
                        timeText = art.publish_date;
                    }
                    return `
                        <div class="timeline-node">
                            <span class="timeline-date">${timeText}</span>
                            <span class="timeline-title">${art.title}</span>
                        </div>
                    `;
                }).join('');
            }
        } catch (error) {
            console.error('Lỗi khi tải dòng thời gian:', error);
        }
    }

    // 5. Quản lý trạng thái cào tin tức
    async function checkScrapingStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            if (data.status === 'success' && data.is_scraping) {
                isScrapingActive = true;
                loadingOverlay.classList.add('active');
                btnScrape.disabled = true;
                btnScrape.textContent = '🔄 Đang cập nhật...';
            } else if (isScrapingActive && !data.is_scraping) {
                // Trạng thái vừa mới chuyển từ bận sang rảnh (cào xong)
                isScrapingActive = false;
                loadingOverlay.classList.remove('active');
                btnScrape.disabled = false;
                btnScrape.textContent = '🔄 Cập nhật tin tức mới';
                
                // Load lại dữ liệu mới nhất
                currentPage = 1;
                loadNews();
                loadStats();
                loadTimeline();
            }
        } catch (e) {
            console.error("Lỗi kiểm tra trạng thái cào:", e);
        }
    }

    // Polling định kỳ kiểm tra trạng thái cào dữ liệu (mỗi 2 giây một lần)
    setInterval(checkScrapingStatus, 2000);

    // Kích hoạt cào tin
    btnScrape.addEventListener('click', async () => {
        const apiKey = localStorage.getItem('gemini_api_key') || '';
        loadingOverlay.classList.add('active');
        loadingText.textContent = apiKey ? "Đang quét các trang báo và tóm tắt bằng Gemini AI..." : "Đang quét các trang báo và xử lý dữ liệu...";
        
        try {
            const response = await fetch('/api/scrape', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_key: apiKey })
            });
            const data = await response.json();
            
            if (data.status === 'success') {
                isScrapingActive = true;
                btnScrape.disabled = true;
                btnScrape.textContent = '🔄 Đang cập nhật...';
            } else {
                alert("Không thể bắt đầu cào: " + data.message);
                loadingOverlay.classList.remove('active');
            }
        } catch (error) {
            console.error("Lỗi kích hoạt cào:", error);
            loadingOverlay.classList.remove('active');
            alert("Lỗi khi kết nối đến máy chủ.");
        }
    });

    // 6. Xử lý các bộ lọc
    // Lọc theo Chuyên mục
    categoryList.querySelectorAll('.menu-item').forEach(item => {
        item.addEventListener('click', () => {
            categoryList.querySelectorAll('.menu-item').forEach(x => x.classList.remove('active'));
            item.classList.add('active');
            currentCategory = item.dataset.category;
            currentPage = 1;
            loadNews();
        });
    });

    // Lọc theo Nguồn tin
    sourceList.querySelectorAll('.menu-item').forEach(item => {
        item.addEventListener('click', () => {
            sourceList.querySelectorAll('.menu-item').forEach(x => x.classList.remove('active'));
            item.classList.add('active');
            currentSource = item.dataset.source;
            currentPage = 1;
            loadNews();
        });
    });

    // Tìm kiếm với chống rung (Debounce)
    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            searchQuery = e.target.value.trim();
            currentPage = 1;
            loadNews();
        }, 500);
    });

    // Phân trang
    btnPrevPage.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            loadNews();
        }
    });

    btnNextPage.addEventListener('click', () => {
        if (currentPage < totalPages) {
            currentPage++;
            loadNews();
        }
    });

    // 7. Khởi động tải dữ liệu ban đầu
    loadNews();
    loadStats();
    loadTimeline();
});
