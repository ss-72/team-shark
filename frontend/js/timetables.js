const API_BASE_URL = 'http://localhost:5000/api';

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
    if (!confirm('条件を満たす時間割を生成し、成功した場合のみ現在の時間割を置き換えます。よろしいですか？')) return;

    const btn = document.getElementById('generate-btn');
    const result = document.getElementById('generate-result');
    btn.disabled = true;
    btn.textContent = '⏳ 生成中...';
    result.style.display = 'none';
    result.innerHTML = '';

    try {
        const res = await fetchAPI('/timetables/generate', { method: 'POST' });

        // 科目別の割当コマ数を集計
        const subjectCounts = {};
        if (res.timetables && res.timetables.length > 0) {
            res.timetables.forEach(t => {
                const name = t.subject_name || `科目ID:${t.subject_id}`;
                subjectCounts[name] = (subjectCounts[name] || 0) + 1;
            });
        }

        let successHtml = `<div class="success-message" style="padding: 12px; border-radius: 6px; background: #e8f5e9; color: #2e7d32; border: 1px solid #c8e6c9;">`;
        successHtml += `<div style="font-weight: bold; font-size: 15px;">✅ ${res.count}件の時間割を自動生成しました</div>`;
        if (Object.keys(subjectCounts).length > 0) {
            successHtml += `<ul style="margin: 8px 0 0 20px; font-size: 13px; line-height: 1.6;">`;
            for (const [sName, count] of Object.entries(subjectCounts)) {
                successHtml += `<li><strong>${escapeHtml(sName)}</strong>: ${count}コマ生成</li>`;
            }
            successHtml += `</ul>`;
        }
        successHtml += `</div>`;

        result.innerHTML = successHtml;
        result.style.display = 'block';
        await loadTimetables();
        showWeekCalendar('all');
    } catch (error) {
        let errorHtml = `<div class="error-message" style="padding: 12px; border-radius: 6px; background: #ffebee; color: #c62828; border: 1px solid #ffcdd2;">`;
        if (error.status === 422 && error.payload && error.payload.shortages) {
            errorHtml += `<div style="font-weight: bold; font-size: 15px;">❌ 時間割を生成できませんでした（条件不足）</div>`;
            errorHtml += `<p style="margin: 6px 0 10px 0; font-size: 13px; color: #555;">以下の科目の必要コマ数を満たせなかったため、直前の時間割が保持されました。</p>`;
            errorHtml += `<div style="display: flex; flex-direction: column; gap: 8px;">`;
            error.payload.shortages.forEach(s => {
                const sName = s.subject_name || `科目ID:${s.subject_id}`;
                let reasonText = s.reason;
                if (s.reason === 'no eligible teacher for subject') {
                    reasonText = '担当可能な教員が登録されていません';
                } else if (s.reason === 'available teacher/time slots are insufficient') {
                    reasonText = '利用可能な教員・時限が不足しています';
                } else if (s.reason === 'assigned periods exceed required periods') {
                    reasonText = '割当コマ数が必要コマ数を超過しています';
                }
                errorHtml += `
                    <div style="background: #fff; padding: 10px 14px; border-radius: 4px; border-left: 4px solid #d32f2f; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                        <div style="font-weight: bold; font-size: 14px; color: #222;">${escapeHtml(sName)}</div>
                        <div style="font-size: 13px; color: #444; margin-top: 4px;">
                            必要: <strong>${s.required}</strong> / 割当可能: <strong>${s.assigned}</strong> / 不足: <strong style="color:#d32f2f;">${s.missing}</strong>
                        </div>
                        <div style="font-size: 12px; color: #d32f2f; margin-top: 4px;">
                            理由: ${escapeHtml(reasonText)}
                        </div>
                    </div>
                `;
            });
            errorHtml += `</div>`;
        } else {
            errorHtml += `<div style="font-weight: bold;">❌ 自動生成に失敗しました: ${escapeHtml(error.message)}</div>`;
        }
        errorHtml += `</div>`;

        result.innerHTML = errorHtml;
        result.style.display = 'block';
    } finally {
        btn.disabled = false;
        btn.textContent = '⚡ 自動生成を実行';
    }
}

// 初期読み込み
loadSelectOptions();
loadTimetables();
