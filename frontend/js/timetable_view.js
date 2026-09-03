// 週間カレンダー表示
const DAY_LABELS = { Monday: '月', Tuesday: '火', Wednesday: '水', Thursday: '木', Friday: '金' };
const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
const PERIODS = [1, 2, 3, 4, 5];

let currentFilter = 'all';
let currentFilterId = null;

async function showWeekCalendar(filter, filterId, filterName) {
    const calendar = document.getElementById('weekly-calendar');
    const loading = document.getElementById('calendar-loading');
    const label = document.getElementById('calendar-filter-label');

    loading.style.display = 'block';
    calendar.innerHTML = '';
    currentFilter = filter || 'all';

    try {
        const timetables = await fetchAPI('/timetables');

        loading.style.display = 'none';

        if (timetables.length === 0) {
            calendar.innerHTML = '<p class="no-data-message">時間割データがありません。「時間割を生成」を実行してください。</p>';
            return;
        }

        // フィルタリング
        let filtered = timetables;
        if (filter === 'teacher' && filterId) {
            filtered = timetables.filter(t => t.teacher_id === filterId);
            label.textContent = `表示中: 教員 ${escapeHtml(filterName || filterId)}`;
        } else if (filter === 'classroom' && filterId) {
            filtered = timetables.filter(t => t.classroom_id === filterId);
            label.textContent = `表示中: 教室 ${escapeHtml(filterName || filterId)}`;
        } else {
            label.textContent = '表示中: 全体';
        }

        // カレンダーグリッドを構築
        let html = '<table class="calendar-table">';
        html += '<thead><tr><th>時限</th>';
        DAYS.forEach(day => {
            html += `<th>${DAY_LABELS[day]}曜日</th>`;
        });
        html += '</tr></thead><tbody>';

        PERIODS.forEach(period => {
            html += `<tr><td class="period-cell">${period}限</td>`;
            DAYS.forEach(day => {
                const entries = filtered.filter(t => t.day_of_week === day && t.period === period);
                if (entries.length === 0) {
                    html += '<td class="empty-cell">−</td>';
                } else if (entries.length === 1) {
                    const t = entries[0];
                    html += `<td class="entry-cell">
                        <div class="entry-subject" style="font-weight: bold; color: #1976d2; margin-bottom: 2px;">${escapeHtml(t.subject_name || '科目ID:' + t.subject_id)}</div>
                        <div class="entry-teacher">${escapeHtml(t.teacher_name || '教員ID:' + t.teacher_id)}</div>
                        <div class="entry-classroom">${escapeHtml(t.classroom_name || '教室ID:' + t.classroom_id)}</div>
                    </td>`;
                } else {
                    // 同じ曜日・時限に複数の授業が入っている場合は、警告ではなく件数と一覧を表示する
                    html += `<td class="multi-entry-cell">
                        <div class="multi-entry-count">${entries.length}件</div>
                        ${entries.map(t => `
                            <div class="multi-entry-item" style="margin-bottom: 4px; padding-bottom: 4px; border-bottom: 1px dashed #e0e0e0;">
                                <div class="entry-subject" style="font-weight: bold; color: #1976d2; margin-bottom: 2px;">${escapeHtml(t.subject_name || '科目ID:' + t.subject_id)}</div>
                                <div class="entry-teacher">${escapeHtml(t.teacher_name || '教員ID:' + t.teacher_id)}</div>
                                <div class="entry-classroom">${escapeHtml(t.classroom_name || '教室ID:' + t.classroom_id)}</div>
                            </div>
                        `).join('')}
                    </td>`;
                }
            });
            html += '</tr>';
        });

        html += '</tbody></table>';
        calendar.innerHTML = html;

        // アクティブなフィルタボタンのスタイルを更新
        document.querySelectorAll('.btn-filter').forEach(btn => btn.classList.remove('active'));
        if (filter === 'teacher') {
            document.querySelector('.btn-filter:nth-child(1)').classList.add('active');
        } else if (filter === 'classroom') {
            document.querySelector('.btn-filter:nth-child(2)').classList.add('active');
        } else {
            document.querySelector('.btn-filter:nth-child(3)').classList.add('active');
        }

    } catch (error) {
        loading.style.display = 'none';
        calendar.innerHTML = '<p class="error-message">カレンダーの読み込みに失敗しました。</p>';
        console.error('Calendar load error:', error);
    }
}

// フィルタ選択用のモーダル表示（教員・教室一覧から選択）
async function showFilterModal(type) {
    try {
        const items = type === 'teacher'
            ? await fetchAPI('/teachers')
            : await fetchAPI('/classrooms');

        const label = type === 'teacher' ? '教員' : '教室';
        const itemList = items.map(item =>
            `<li onclick="showWeekCalendar('${type}', ${item.id}, '${escapeHtml(item.name)}')" class="filter-item">
                ${escapeHtml(item.name)}
            </li>`
        ).join('');

        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content">
                <h3>${label}を選択</h3>
                <ul class="filter-list">${itemList}</ul>
                <button onclick="this.closest('.modal-overlay').remove()" class="btn-close">閉じる</button>
            </div>
        `;
        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    } catch (error) {
        alert(`${type === 'teacher' ? '教員' : '教室'}一覧の取得に失敗しました`);
    }
}

// カレンダー初期表示
document.addEventListener('DOMContentLoaded', () => {
    showWeekCalendar('all');
});