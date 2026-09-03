const LOGIN_API_URL = 'http://localhost:5000/api';

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
            window.location.href = 'pages/subjects.html';
        }
    } catch (err) {
        error.textContent = err.message;
        error.style.display = 'block';
    }
});
