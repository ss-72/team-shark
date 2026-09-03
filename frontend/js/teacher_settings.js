const API_BASE_URL = 'http://localhost:5000/api';
const teacherId = Number(new URLSearchParams(window.location.search).get('id'));
const dayLabels = { Monday: '月曜日', Tuesday: '火曜日', Wednesday: '水曜日', Thursday: '木曜日', Friday: '金曜日' };

async function fetchAPI(endpoint, options = {}) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, { headers: { 'Content-Type': 'application/json' }, credentials: 'include', ...options });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    return data;
}
function showError(message) { const el = document.getElementById('page-error'); el.textContent = message; el.style.display = 'block'; }
function escapeHtml(value) { const el = document.createElement('div'); el.textContent = value; return el.innerHTML; }

async function loadPage() {
    if (!Number.isInteger(teacherId) || teacherId < 1) { showError('教員IDが指定されていません。'); return; }
    try {
        const [teacher, subjects] = await Promise.all([fetchAPI(`/teachers/${teacherId}`), fetchAPI('/subjects')]);
        document.getElementById('page-title').textContent = `${teacher.name} の担当・NG時間設定`;
        document.getElementById('subject-id').innerHTML = '<option value="">-- 科目を選択 --</option>' + subjects.map(s => `<option value="${s.id}">${escapeHtml(s.name)}</option>`).join('');
        await Promise.all([loadAssignments(), loadUnavailability()]);
    } catch (error) { showError(error.message); }
}
async function loadAssignments() {
    const assignments = await fetchAPI(`/teachers/${teacherId}/subjects`);
    document.getElementById('assignment-list').innerHTML = assignments.map(a => `<tr><td>${escapeHtml(a.subject.name)}</td><td><button class="btn-delete" onclick="removeAssignment(${a.subject_id})">削除</button></td></tr>`).join('');
}
async function loadUnavailability() {
    const slots = await fetchAPI(`/teachers/${teacherId}/unavailable-slots`);
    document.getElementById('unavailability-list').innerHTML = slots.map(slot => `<tr><td>${dayLabels[slot.day_of_week]}</td><td>${slot.period === null ? '終日' : `${slot.period}限`}</td><td><button class="btn-delete" onclick="removeUnavailability(${slot.id})">削除</button></td></tr>`).join('');
}
document.getElementById('assignment-form').addEventListener('submit', async event => { event.preventDefault(); try { await fetchAPI(`/teachers/${teacherId}/subjects`, { method: 'POST', body: JSON.stringify({ subject_id: Number(document.getElementById('subject-id').value) }) }); loadAssignments(); } catch (error) { showError(error.message); } });
document.getElementById('unavailability-form').addEventListener('submit', async event => { event.preventDefault(); const value = document.getElementById('period').value; try { await fetchAPI(`/teachers/${teacherId}/unavailable-slots`, { method: 'POST', body: JSON.stringify({ day_of_week: document.getElementById('day-of-week').value, period: value === '' ? null : Number(value) }) }); loadUnavailability(); } catch (error) { showError(error.message); } });
async function removeAssignment(subjectId) { try { await fetchAPI(`/teachers/${teacherId}/subjects/${subjectId}`, { method: 'DELETE' }); loadAssignments(); } catch (error) { showError(error.message); } }
async function removeUnavailability(slotId) { try { await fetchAPI(`/teachers/${teacherId}/unavailable-slots/${slotId}`, { method: 'DELETE' }); loadUnavailability(); } catch (error) { showError(error.message); } }
loadPage();
