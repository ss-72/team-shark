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

async function loadTimeSlots() {
    const loading = document.getElementById('loading');
    const table = document.getElementById('timeslot-table');
    const noData = document.getElementById('no-data');
    const tbody = document.getElementById('timeslot-list');

    loading.style.display = 'block';
    table.style.display = 'none';
    noData.style.display = 'none';

    try {
        const slots = await fetchAPI('/time_slots');
        loading.style.display = 'none';

        if (slots.length === 0) {
            noData.style.display = 'block';
            return;
        }

        table.style.display = '';
        tbody.innerHTML = slots.map(s => `
            <tr>
                <td>${s.id}</td>
                <td>${s.period}</td>
                <td>${s.floor ?? ''}</td>
                <td>${s.start_time}</td>
                <td>${s.end_time}</td>
                <td class="action-btns">
                    <button onclick="editTimeSlot(${s.id})" class="btn-edit">編集</button>
                    <button onclick="deleteTimeSlot(${s.id})" class="btn-delete">削除</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        loading.textContent = 'データの読み込みに失敗しました。';
    }
}

document.getElementById('timeslot-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const errorEl = document.getElementById('form-error');
    errorEl.style.display = 'none';

    const id = document.getElementById('timeslot-id').value;
    const period = document.getElementById('period').value;
    const floor = document.getElementById('floor').value;
    const start_time = document.getElementById('start_time').value.trim();
    const end_time = document.getElementById('end_time').value.trim();

    if (!period || !start_time || !end_time) {
        showFormError('時限・開始時間・終了時間は必須です。');
        return;
    }

    const body = {
        period: parseInt(period),
        floor: floor ? parseInt(floor) : null,
        start_time,
        end_time,
    };

    try {
        if (id) {
            await fetchAPI(`/time_slots/${id}`, {
                method: 'PUT',
                body: JSON.stringify(body),
            });
        } else {
            await fetchAPI('/time_slots', {
                method: 'POST',
                body: JSON.stringify(body),
            });
        }
        resetForm();
        await loadTimeSlots();
    } catch (error) {
        showFormError(error.message);
    }
});

async function editTimeSlot(id) {
    try {
        const slot = await fetchAPI(`/time_slots/${id}`);
        document.getElementById('timeslot-id').value = slot.id;
        document.getElementById('period').value = slot.period;
        document.getElementById('floor').value = slot.floor ?? '';
        document.getElementById('start_time').value = slot.start_time;
        document.getElementById('end_time').value = slot.end_time;

        document.getElementById('form-title').textContent = '編集';
        document.getElementById('submit-btn').textContent = '更新';
        document.getElementById('cancel-btn').style.display = '';

        window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (error) {
        alert('時間枠データの取得に失敗しました: ' + error.message);
    }
}

async function deleteTimeSlot(id) {
    if (!confirm('この時間枠を削除してもよろしいですか？')) return;

    try {
        await fetchAPI(`/time_slots/${id}`, { method: 'DELETE' });
        await loadTimeSlots();
    } catch (error) {
        alert('削除に失敗しました: ' + error.message);
    }
}

function resetForm() {
    document.getElementById('timeslot-form').reset();
    document.getElementById('timeslot-id').value = '';
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

loadTimeSlots();