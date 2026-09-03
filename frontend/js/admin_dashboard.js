// 管理者ダッシュボード スクリプト
(function () {
    const API_BASE = 'http://localhost:5000/api';

    async function fetchCount(endpoint) {
        try {
            const res = await fetch(`${API_BASE}${endpoint}`, { credentials: 'include' });
            if (!res.ok) return 0;
            const data = await res.json();
            return Array.isArray(data) ? data.length : 0;
        } catch (e) {
            console.error(`Error fetching ${endpoint}:`, e);
            return 0;
        }
    }

    async function loadStats() {
        const [timetablesCount, subjectsCount, teachersCount, classroomsCount] = await Promise.all([
            fetchCount('/timetables'),
            fetchCount('/subjects'),
            fetchCount('/teachers'),
            fetchCount('/classrooms'),
        ]);

        const elTimetables = document.getElementById('stat-timetables');
        const elSubjects = document.getElementById('stat-subjects');
        const elTeachers = document.getElementById('stat-teachers');
        const elClassrooms = document.getElementById('stat-classrooms');

        if (elTimetables) elTimetables.textContent = `${timetablesCount} 件`;
        if (elSubjects) elSubjects.textContent = `${subjectsCount} 件`;
        if (elTeachers) elTeachers.textContent = `${teachersCount} 名`;
        if (elClassrooms) elClassrooms.textContent = `${classroomsCount} 室`;
    }

    document.addEventListener('DOMContentLoaded', loadStats);
})();
