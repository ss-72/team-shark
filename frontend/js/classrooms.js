const API_BASE_URL = 'http://localhost:5000/api';

async function fetchAPI(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            headers: { 'Content-Type': 'application/json' },
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

async function loadClassrooms() {
    const loading = document.getElementById('loading');
    const table = document.getElementById('classroom-table');
    const noData = document.getElementById('no-data');
    const tbody = document.getElementById('classroom-list');

    loading.style.display = 'block';
    table.style.display = 'none';
    noData.style.display = 'none';

    try {
        const classrooms = await fetchAPI('/classrooms');
        loading.style.display = 'none';

        if (classrooms.length === 0) {
            noData.style.display = 'block';
            return;
        }

        table.style.display = '';
        tbody.innerHTML = classrooms.map(c => `
            <tr>
                <td>${c.id}</td>
                <td>${escapeHtml(c.name)}</td>
                <td>${c.capacity ?? ''}</td>
                <td>${c.floor ?? ''}</td>
                <td>${escapeHtml(c.priority_department || '')}</td>
                <td class="action-btns">
                    <button onclick="editClassroom(${c.id})" class="btn-edit">編集</button>
                    <button onclick="deleteClassroom(${c.id})" class="btn-delete">削除</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        loading.textContent = 'データの読み込みに失敗しました。';
    }
}

document.getElementById('classroom-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const errorEl = document.getElementById('form-error');
    errorEl.style.display = 'none';

    const id = document.getElementById('classroom-id').value;
    const name = document.getElementById('name').value.trim();
    const capacity = document.getElementById('capacity').value;
    const floor = document.getElementById('floor').value;
    const priority_department = document.getElementById('priority_department').value.trim();

    if (!name) {
        showFormError('教室名は必須です。');
        return;
    }

    const body = {
        name,
        capacity: capacity ? parseInt(capacity) : null,
        floor: floor ? parseInt(floor) : null,
        priority_department: priority_department || null,
    };

    try {
        if (id) {
            await fetchAPI(`/classrooms/${id}`, {
                method: 'PUT',
                body: JSON.stringify(body),
            });
        } else {
            await fetchAPI('/classrooms', {
                method: 'POST',
                body: JSON.stringify(body),
            });
        }
        resetForm();
        await loadClassrooms();
    } catch (error) {
        showFormError(error.message);
    }
});

async function editClassroom(id) {
    try {
        const classroom = await fetchAPI(`/classrooms/${id}`);
        document.getElementById('classroom-id').value = classroom.id;
        document.getElementById('name').value = classroom.name;
        document.getElementById('capacity').value = classroom.capacity ?? '';
        document.getElementById('floor').value = classroom.floor ?? '';
        document.getElementById('priority_department').value = classroom.priority_department || '';

        document.getElementById('form-title').textContent = '編集';
        document.getElementById('submit-btn').textContent = '更新';
        document.getElementById('cancel-btn').style.display = '';

        window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (error) {
        alert('教室データの取得に失敗しました: ' + error.message);
    }
}

async function deleteClassroom(id) {
    if (!confirm('この教室を削除してもよろしいですか？')) return;

    try {
        await fetchAPI(`/classrooms/${id}`, { method: 'DELETE' });
        await loadClassrooms();
    } catch (error) {
        alert('削除に失敗しました: ' + error.message);
    }
}

function resetForm() {
    document.getElementById('classroom-form').reset();
    document.getElementById('classroom-id').value = '';
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

loadClassrooms();