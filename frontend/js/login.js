const LOGIN_API_URL = 'http://localhost:5000/api';

// URLパラメータに ?demo=1 がある場合のみクイック入力を表示
document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('demo') === '1') {
        const demoSection = document.getElementById('demo-quick-section');
        if (demoSection) {
            demoSection.style.display = 'block';
        }
    }
});

function fillAdmin() {
    document.getElementById('login-username').value = 'admin';
    document.getElementById('login-password').value = 'adminpassword123';
}

function fillTeacher() {
    document.getElementById('login-username').value = 'teacher';
    document.getElementById('login-password').value = 'teacher123';
}

document.getElementById('login-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const error = document.getElementById('login-error');
    error.style.display = 'none';

    try {
        const response = await fetch(`${LOGIN_API_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                username: document.getElementById('login-username').value,
                password: document.getElementById('login-password').value,
            }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);

        const user = data.user || {};
        if (user.role === 'teacher') {
            window.location.href = 'pages/my_timetable.html';
        } else {
            window.location.href = 'pages/admin_dashboard.html';
        }
    } catch (err) {
        const msg = (err.message || '').toLowerCase();
        if (msg.includes('invalid credentials')) {
            error.textContent = 'ユーザー名またはパスワードが正しくありません。';
        } else if (msg.includes('username and password required')) {
            error.textContent = 'ユーザー名とパスワードを入力してください。';
        } else {
            error.textContent = err.message || 'ログインに失敗しました。';
        }
        error.style.display = 'block';
    }
});
