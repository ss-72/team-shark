const API_BASE_URL = 'http://localhost:5000/api';

async function fetchAPI(endpoint, options = {}) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        ...options,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    return data;
}

async function loadSubjects() {
    const loading = document.getElementById('loading');
    const table = document.getElementById('subject-table');
    const noData = document.getElementById('no-data');
    try {
        const subjects = await fetchAPI('/subjects');
        loading.style.display = 'none';
        table.style.display = subjects.length ? '' : 'none';
        noData.style.display = subjects.length ? 'none' : 'block';
        document.getElementById('subject-list').innerHTML = subjects.map(subject => `
            <tr><td>${subject.id}</td><td>${escapeHtml(subject.name)}</td><td>${subject.required_periods_per_week}</td>
            <td class="action-btns"><button class="btn-edit" onclick="editSubject(${subject.id})">編集</button><button class="btn-delete" onclick="deleteSubject(${subject.id})">削除</button></td></tr>
        `).join('');
    } catch (error) { loading.textContent = 'データの読み込みに失敗しました。'; }
}

document.getElementById('subject-form').addEventListener('submit', async event => {
    event.preventDefault();
    const id = document.getElementById('subject-id').value;
    const name = document.getElementById('name').value.trim();
    const required_periods_per_week = Number(document.getElementById('required-periods').value);
    try {
        await fetchAPI(id ? `/subjects/${id}` : '/subjects', {
            method: id ? 'PUT' : 'POST', body: JSON.stringify({ name, required_periods_per_week }),
        });
        resetForm();
        loadSubjects();
    } catch (error) { showError(error.message); }
});

async function editSubject(id) {
    try {
        const subject = await fetchAPI(`/subjects/${id}`);
        document.getElementById('subject-id').value = subject.id;
        document.getElementById('name').value = subject.name;
        document.getElementById('required-periods').value = subject.required_periods_per_week;
        document.getElementById('form-title').textContent = '編集';
        document.getElementById('submit-btn').textContent = '更新';
        document.getElementById('cancel-btn').style.display = '';
    } catch (error) { alert(error.message); }
}

async function deleteSubject(id) {
    if (!confirm('この科目を削除してもよろしいですか？')) return;
    try { await fetchAPI(`/subjects/${id}`, { method: 'DELETE' }); loadSubjects(); } catch (error) { alert(error.message); }
}

function resetForm() {
    document.getElementById('subject-form').reset();
    document.getElementById('subject-id').value = '';
    document.getElementById('required-periods').value = 1;
    document.getElementById('form-title').textContent = '新規登録';
    document.getElementById('submit-btn').textContent = '登録';
    document.getElementById('cancel-btn').style.display = 'none';
    document.getElementById('form-error').style.display = 'none';
}
function showError(message) { const el = document.getElementById('form-error'); el.textContent = message; el.style.display = 'block'; }
function escapeHtml(value) { const el = document.createElement('div'); el.textContent = value; return el.innerHTML; }
document.getElementById('cancel-btn').addEventListener('click', resetForm);
loadSubjects();
