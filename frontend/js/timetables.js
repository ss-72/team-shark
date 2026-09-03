const API_BASE_URL = 'http://localhost:5000/api';

async function fetchAPI(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            ...options,
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || `HTTP ${response.status}`);
        }
        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// 教員・教室の選択肢を読み込む
async function loadSelectOptions() {
    try {
        const [teachers, subjects, classrooms] = await Promise.all([
            fetchAPI('/teachers'),
            fetchAPI('/subjects'),
            fetchAPI('/classrooms'),
        ]);
        const teacherSelect = document.getElementById('teacher_id');
        const subjectSelect = document.getElementById('subject_id');
        const classroomSelect = document.getElementById('classroom_id');

        teacherSelect.innerHTML = '<option value="">-- 選択 --</option>' +
            teachers.map(t => `<option value="${t.id}">${escapeHtml(t.name)}</option>`).join('');

        subjectSelect.innerHTML = '<option value="">-- 選択 --</option>' +
            subjects.map(s => `<option value="${s.id}">${escapeHtml(s.name)}</option>`).join('');

        classroomSelect.innerHTML = '<option value="">-- 選択 --</option>' +
            classrooms.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('');
    } catch (error) {
        console.error('選択肢の読み込みに失敗:', error);
    }
}

async function loadTimetables() {
    const loading = document.getElementById('loading');
    const table = document.getElementById('timetable-table');
    const noData = document.getElementById('no-data');
    const tbody = document.getElementById('timetable-list');

    loading.style.display = 'block';
    table.style.display = 'none';
    noData.style.display = 'none';

    try {
        const timetables = await fetchAPI('/timetables');
        loading.style.display = 'none';

        if (timetables.length === 0) {
            noData.style.display = 'block';
            return;
        }

        const dayLabels = { Monday: '月', Tuesday: '火', Wednesday: '水', Thursday: '木', Friday: '金' };

        table.style.display = '';
        tbody.innerHTML = timetables.map(t => `
            <tr>
                <td>${t.id}</td>
                <td>${dayLabels[t.day_of_week] || t.day_of_week}</td>
                <td>${t.period}</td>
                <td>${escapeHtml(t.teacher_name || '教員ID:' + t.teacher_id)}</td>
                <td>${escapeHtml(t.subject_name || '科目ID:' + t.subject_id)}</td>
                <td>${escapeHtml(t.classroom_name || '教室ID:' + t.classroom_id)}</td>
                <td class="action-btns">
                    <button onclick="editTimetable(${t.id})" class="btn-edit">編集</button>
                    <button onclick="deleteTimetable(${t.id})" class="btn-delete">削除</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        loading.textContent = 'データの読み込みに失敗しました。';
    }
}

document.getElementById('timetable-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const errorEl = document.getElementById('form-error');
    errorEl.style.display = 'none';

    const id = document.getElementById('timetable-id').value;
    const day_of_week = document.getElementById('day_of_week').value;
    const period = document.getElementById('period').value;
    const teacher_id = document.getElementById('teacher_id').value;
    const subject_id = document.getElementById('subject_id').value;
    const classroom_id = document.getElementById('classroom_id').value;
    const is_online = document.getElementById('is_online').checked;

    if (!day_of_week || !period || !teacher_id || !subject_id || !classroom_id) {
        showFormError('すべての必須項目を入力してください。');
        return;
    }

    const body = {
        day_of_week,
        period: parseInt(period),
        teacher_id: parseInt(teacher_id),
        subject_id: parseInt(subject_id),
        classroom_id: parseInt(classroom_id),
        is_online: is_online,
    };

    try {
        if (id) {
            await fetchAPI(`/timetables/${id}`, {
                method: 'PUT',
                body: JSON.stringify(body),
            });
        } else {
            await fetchAPI('/timetables', {
                method: 'POST',
                body: JSON.stringify(body),
            });
        }
        resetForm();
        await loadTimetables();
    } catch (error) {
        showFormError(error.message);
    }
});

async function editTimetable(id) {
    try {
        const [timetable] = await Promise.all([
            fetchAPI(`/timetables/${id}`),
            loadSelectOptions(),
        ]);
        document.getElementById('timetable-id').value = timetable.id;
        document.getElementById('day_of_week').value = timetable.day_of_week;
        document.getElementById('period').value = timetable.period;
        document.getElementById('teacher_id').value = timetable.teacher_id;
        document.getElementById('subject_id').value = timetable.subject_id;
        document.getElementById('classroom_id').value = timetable.classroom_id;
        document.getElementById('is_online').checked = timetable.is_online;

        document.getElementById('form-title').textContent = '編集';
        document.getElementById('submit-btn').textContent = '更新';
        document.getElementById('cancel-btn').style.display = '';

        window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (error) {
        alert('時間割データの取得に失敗しました: ' + error.message);
    }
}

async function deleteTimetable(id) {
    if (!confirm('この時間割を削除してもよろしいですか？')) return;

    try {
        await fetchAPI(`/timetables/${id}`, { method: 'DELETE' });
        await loadTimetables();
    } catch (error) {
        alert('削除に失敗しました: ' + error.message);
    }
}

function resetForm() {
    document.getElementById('timetable-form').reset();
    document.getElementById('timetable-id').value = '';
    document.getElementById('is_online').checked = false;
    document.getElementById('form-title').textContent = '新規登録';
    document.getElementById('submit-btn').textContent = '登録';
    document.getElementById('cancel-btn').style.display = 'none';
    document.getElementById('form-error').style.display = 'none';
}

function showFormError(message) {
    const el = document.getElementById('form-error');
    el.textContent = message;
    el.style.display = 'block';
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// 自動生成
async function generateTimetable() {
    if (!confirm('現在の時間割を全て削除して、自動生成を実行します。よろしいですか？')) return;

    const btn = document.getElementById('generate-btn');
    const result = document.getElementById('generate-result');
    btn.disabled = true;
    btn.textContent = '⏳ 生成中...';
    result.style.display = 'none';

    try {
        const res = await fetchAPI('/timetables/generate', { method: 'POST' });
        result.textContent = `✅ ${res.count}件の時間割を自動生成しました`;
        result.className = 'success-message';
        result.style.display = 'block';
        await loadTimetables();
        showWeekCalendar('all');
    } catch (error) {
        result.textContent = '❌ 自動生成に失敗しました: ' + error.message;
        result.className = 'error-message';
        result.style.display = 'block';
    } finally {
        btn.disabled = false;
        btn.textContent = '⚡ 自動生成を実行';
    }
}

// 初期読み込み
loadSelectOptions();
loadTimetables();
