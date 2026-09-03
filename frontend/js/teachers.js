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

async function loadTeachers() {
    const loading = document.getElementById('loading');
    const table = document.getElementById('teacher-table');
    const noData = document.getElementById('no-data');
    const tbody = document.getElementById('teacher-list');

    loading.style.display = 'block';
    table.style.display = 'none';
    noData.style.display = 'none';

    try {
        const teachers = await fetchAPI('/teachers');
        loading.style.display = 'none';

        if (teachers.length === 0) {
            noData.style.display = 'block';
            return;
        }

        table.style.display = '';
        tbody.innerHTML = teachers.map(t => `
            <tr>
                <td>${t.id}</td>
                <td>${escapeHtml(t.name)}</td>
                <td>${escapeHtml(t.employment_type || '')}</td>
                <td>${escapeHtml(t.department || '')}</td>
                <td>${escapeHtml(t.subject || '')}</td>
                <td><a class="btn-edit" href="teacher_settings.html?id=${t.id}">設定</a></td>
                <td class="action-btns">
                    <button onclick="editTeacher(${t.id})" class="btn-edit">編集</button>
                    <button onclick="deleteTeacher(${t.id})" class="btn-delete">削除</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        loading.textContent = 'データの読み込みに失敗しました。';
    }
}

document.getElementById('teacher-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const errorEl = document.getElementById('form-error');
    errorEl.style.display = 'none';

    const id = document.getElementById('teacher-id').value;
    const name = document.getElementById('name').value.trim();
    const employment_type = document.getElementById('employment_type').value;
    const department = document.getElementById('department').value.trim();
    const subject = document.getElementById('subject').value.trim();

    if (!name) {
        showFormError('教員名は必須です。');
        return;
    }

    const body = { name, employment_type, department, subject };

    try {
        if (id) {
            await fetchAPI(`/teachers/${id}`, {
                method: 'PUT',
                body: JSON.stringify(body),
            });
        } else {
            await fetchAPI('/teachers', {
                method: 'POST',
                body: JSON.stringify(body),
            });
        }
        resetForm();
        await loadTeachers();
    } catch (error) {
        showFormError(error.message);
    }
});

async function editTeacher(id) {
    try {
        const teacher = await fetchAPI(`/teachers/${id}`);
        document.getElementById('teacher-id').value = teacher.id;
        document.getElementById('name').value = teacher.name;
        document.getElementById('employment_type').value = teacher.employment_type || '';
        document.getElementById('department').value = teacher.department || '';
        document.getElementById('subject').value = teacher.subject || '';

        document.getElementById('form-title').textContent = '編集';
        document.getElementById('submit-btn').textContent = '更新';
        document.getElementById('cancel-btn').style.display = '';

        window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (error) {
        alert('教員データの取得に失敗しました: ' + error.message);
    }
}

async function deleteTeacher(id) {
    if (!confirm('この教員を削除してもよろしいですか？')) return;

    try {
        await fetchAPI(`/teachers/${id}`, { method: 'DELETE' });
        await loadTeachers();
    } catch (error) {
        alert('削除に失敗しました: ' + error.message);
    }
}

function resetForm() {
    document.getElementById('teacher-form').reset();
    document.getElementById('teacher-id').value = '';
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

// Initial load
loadTeachers();
