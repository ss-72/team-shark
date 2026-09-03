const API_BASE_URL = 'http://localhost:5000/api';
const teacherId = Number(new URLSearchParams(window.location.search).get('id'));
const dayLabels = {
    Monday: '月曜日',
    Tuesday: '火曜日',
    Wednesday: '水曜日',
    Thursday: '木曜日',
    Friday: '金曜日',
};

async function fetchAPI(endpoint, options = {}) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        ...options,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    return data;
}

function showError(message) {
    const el = document.getElementById('page-error');
    el.textContent = message;
    el.style.display = 'block';
}

function clearError() {
    const el = document.getElementById('page-error');
    el.textContent = '';
    el.style.display = 'none';
}

function escapeHtml(value) {
    if (!value) return '';
    const el = document.createElement('div');
    el.textContent = value;
    return el.innerHTML;
}

async function loadPage() {
    if (!Number.isInteger(teacherId) || teacherId < 1) {
        showError('教員IDが正しく指定されていません。教員一覧から再度選択してください。');
        return;
    }
    try {
        const [teacher, subjects] = await Promise.all([
            fetchAPI(`/teachers/${teacherId}`),
            fetchAPI('/subjects'),
        ]);
        document.getElementById('page-title').textContent = `${escapeHtml(teacher.name)} 先生の授業条件設定`;
        document.getElementById('subject-id').innerHTML = '<option value="">-- 科目を選択してください --</option>' +
            subjects.map(s => `<option value="${s.id}">${escapeHtml(s.name)} (必要: 週${s.required_periods || 1}コマ)</option>`).join('');

        await Promise.all([loadAssignments(), loadUnavailability()]);
    } catch (error) {
        showError('教員データの取得に失敗しました: ' + error.message);
    }
}

async function loadAssignments() {
    try {
        const assignments = await fetchAPI(`/teachers/${teacherId}/subjects`);
        const tbody = document.getElementById('assignment-list');
        const noData = document.getElementById('no-assignment');

        if (!assignments || assignments.length === 0) {
            tbody.innerHTML = '';
            if (noData) noData.style.display = 'block';
            return;
        }

        if (noData) noData.style.display = 'none';
        tbody.innerHTML = assignments.map(a => `
            <tr>
                <td><strong>${escapeHtml(a.subject ? a.subject.name : '科目ID:' + a.subject_id)}</strong></td>
                <td>
                    <button class="btn-delete" onclick="removeAssignment(${a.subject_id})">削除</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        showError('担当可能科目の取得に失敗しました: ' + error.message);
    }
}

async function loadUnavailability() {
    try {
        const slots = await fetchAPI(`/teachers/${teacherId}/unavailable-slots`);
        const tbody = document.getElementById('unavailability-list');
        const noData = document.getElementById('no-unavailability');

        if (!slots || slots.length === 0) {
            tbody.innerHTML = '';
            if (noData) noData.style.display = 'block';
            return;
        }

        if (noData) noData.style.display = 'none';
        tbody.innerHTML = slots.map(slot => `
            <tr>
                <td>${dayLabels[slot.day_of_week] || slot.day_of_week}</td>
                <td>${slot.period === null ? '<strong>終日</strong>' : `${slot.period}限`}</td>
                <td>
                    <button class="btn-delete" onclick="removeUnavailability(${slot.id})">削除</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        showError('出勤条件の取得に失敗しました: ' + error.message);
    }
}

document.getElementById('assignment-form').addEventListener('submit', async event => {
    event.preventDefault();
    clearError();
    const subjectId = Number(document.getElementById('subject-id').value);
    if (!subjectId) return;

    try {
        await fetchAPI(`/teachers/${teacherId}/subjects`, {
            method: 'POST',
            body: JSON.stringify({ subject_id: subjectId }),
        });
        document.getElementById('subject-id').value = '';
        await loadAssignments();
    } catch (error) {
        showError(error.message);
    }
});

document.getElementById('unavailability-form').addEventListener('submit', async event => {
    event.preventDefault();
    clearError();
    const periodValue = document.getElementById('period').value;
    try {
        await fetchAPI(`/teachers/${teacherId}/unavailable-slots`, {
            method: 'POST',
            body: JSON.stringify({
                day_of_week: document.getElementById('day-of-week').value,
                period: periodValue === '' ? null : Number(periodValue),
            }),
        });
        await loadUnavailability();
    } catch (error) {
        showError(error.message);
    }
});

async function removeAssignment(subjectId) {
    if (!confirm('この担当可能科目を削除してもよろしいですか？')) return;
    clearError();
    try {
        await fetchAPI(`/teachers/${teacherId}/subjects/${subjectId}`, { method: 'DELETE' });
        await loadAssignments();
    } catch (error) {
        showError(error.message);
    }
}

async function removeUnavailability(slotId) {
    if (!confirm('この出勤不可条件を削除してもよろしいですか？')) return;
    clearError();
    try {
        await fetchAPI(`/teachers/${teacherId}/unavailable-slots/${slotId}`, { method: 'DELETE' });
        await loadUnavailability();
    } catch (error) {
        showError(error.message);
    }
}

loadPage();
