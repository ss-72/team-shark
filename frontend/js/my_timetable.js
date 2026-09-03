const API_BASE_URL = 'http://localhost:5000/api';

const DAY_LABELS = {
    Monday: '月曜日',
    Tuesday: '火曜日',
    Wednesday: '水曜日',
    Thursday: '木曜日',
    Friday: '金曜日',
};

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

async function fetchAPI(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            ...options,
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            const err = new Error(data.error || `HTTP ${response.status}`);
            err.status = response.status;
            err.payload = data;
            throw err;
        }
        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

async function init() {
    const loading = document.getElementById('loading');
    const table = document.getElementById('my-timetable-table');
    const noData = document.getElementById('no-data');
    const errorEl = document.getElementById('error');
    const userInfo = document.getElementById('user-info');
    const tbody = document.getElementById('my-timetable-list');

    loading.style.display = 'block';
    table.style.display = 'none';
    noData.style.display = 'none';
    errorEl.style.display = 'none';

    try {
        // ログイン状態確認
        const user = await fetchAPI('/auth/me');
        if (user.role !== 'teacher') {
            userInfo.textContent = `${escapeHtml(user.username)} (${user.role})`;
            loading.style.display = 'none';
            errorEl.innerHTML = `この画面は教員専用です。<a href="admin_dashboard.html" style="color: #2563eb; text-decoration: underline;">管理者ダッシュボード</a> をご利用ください。`;
            errorEl.style.display = 'block';
            return;
        }

        const teacherName = user.teacher_name || user.username;
        userInfo.textContent = `${escapeHtml(teacherName)} 先生`;

        // 自分の時間割取得
        const timetables = await fetchAPI('/my/timetable');
        loading.style.display = 'none';

        if (!timetables || timetables.length === 0) {
            noData.style.display = 'block';
            return;
        }

        tbody.innerHTML = timetables.map(t => `
            <tr>
                <td>${DAY_LABELS[t.day_of_week] || escapeHtml(t.day_of_week)}</td>
                <td><strong>${escapeHtml(String(t.period))}限</strong></td>
                <td><strong>${escapeHtml(t.subject || t.subject_name || '科目ID:' + t.subject_id)}</strong></td>
                <td>${escapeHtml(t.classroom || t.classroom_name || '教室ID:' + t.classroom_id)}</td>
            </tr>
        `).join('');

        table.style.display = '';
    } catch (err) {
        loading.style.display = 'none';
        if (err.status === 401) {
            window.location.href = '../index.html';
            return;
        }
        errorEl.textContent = '時間割の取得に失敗しました: ' + err.message;
        errorEl.style.display = 'block';
    }
}

async function handleLogout() {
    try {
        await fetchAPI('/auth/logout', { method: 'POST' });
    } catch (e) {
        console.error('Logout error:', e);
    }
    window.location.href = '../index.html';
}

document.addEventListener('DOMContentLoaded', init);
