// 管理画面共通ナビゲーション & 認証制御スクリプト
(function () {
    const API_BASE = 'http://localhost:5000/api';

    // 共通ヘッダーHTMLの生成
    function renderAdminHeader(container, activeKey) {
        container.className = 'app-header';
        container.innerHTML = `
            <div class="header-brand-nav">
                <a href="admin_dashboard.html" class="brand-logo">
                    <span class="brand-name">Schedule Connect</span>
                    <span class="system-tag">管理システム</span>
                </a>
                <nav class="nav-links">
                    <a href="admin_dashboard.html" data-nav="dashboard" class="${activeKey === 'dashboard' ? 'active' : ''}">ダッシュボード</a>
                    <a href="timetables.html" data-nav="timetables" class="${activeKey === 'timetables' ? 'active' : ''}">時間割</a>
                    <a href="subjects.html" data-nav="subjects" class="${activeKey === 'subjects' ? 'active' : ''}">科目</a>
                    <a href="teachers.html" data-nav="teachers" class="${activeKey === 'teachers' ? 'active' : ''}">教員</a>
                    <a href="classrooms.html" data-nav="classrooms" class="${activeKey === 'classrooms' ? 'active' : ''}">教室</a>
                    <a href="time_slots.html" data-nav="time_slots" class="${activeKey === 'time_slots' ? 'active' : ''}">時間枠</a>
                </nav>
            </div>
            <div class="nav-user-area">
                <span class="user-badge" id="nav-user-label">管理者: 確認中...</span>
                <button type="button" class="btn-logout" id="header-logout-btn">ログアウト</button>
            </div>
        `;

        const logoutBtn = container.querySelector('#header-logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', handleAdminLogout);
        }
    }

    // 現在のページ判定
    function getCurrentNavKey() {
        const path = window.location.pathname;
        if (path.endsWith('admin_dashboard.html')) return 'dashboard';
        if (path.endsWith('timetables.html')) return 'timetables';
        if (path.endsWith('subjects.html')) return 'subjects';
        if (path.endsWith('teachers.html') || path.endsWith('teacher_settings.html')) return 'teachers';
        if (path.endsWith('classrooms.html')) return 'classrooms';
        if (path.endsWith('time_slots.html')) return 'time_slots';
        return '';
    }

    // ログアウト処理
    window.handleAdminLogout = async function () {
        try {
            await fetch(`${API_BASE}/auth/logout`, {
                method: 'POST',
                credentials: 'include',
            });
        } catch (e) {
            console.error('Logout error:', e);
        }
        window.location.href = '../index.html';
    };

    // 認証チェックとユーザー名表示
    async function checkAuthAndInitHeader() {
        const headerEl = document.getElementById('common-admin-header') || document.querySelector('.app-header');
        const activeKey = getCurrentNavKey();

        if (headerEl) {
            renderAdminHeader(headerEl, activeKey);
        }

        try {
            const res = await fetch(`${API_BASE}/auth/me`, {
                credentials: 'include',
            });
            if (res.status === 401) {
                window.location.href = '../index.html';
                return;
            }
            const data = await res.json().catch(() => ({}));
            if (data.role === 'teacher') {
                // 教員は教員専用時間割画面へ誘導
                window.location.href = 'my_timetable.html';
                return;
            }

            const userLabel = document.getElementById('nav-user-label');
            if (userLabel) {
                userLabel.textContent = `管理者: ${data.username || 'admin'}`;
            }
        } catch (err) {
            console.error('Auth check error:', err);
        }
    }

    document.addEventListener('DOMContentLoaded', checkAuthAndInitHeader);
})();
