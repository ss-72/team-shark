"""
UI/UX 業務システム化の動作確認スクリプト (Flask Test Client使用)
- 静的ファイル配信 (index.html, admin_dashboard.html, admin_nav.js)
- adminログインとrole確認
- teacherログインとrole確認
- 各管理画面APIと自動生成APIのレスポンス検証
- 422不足理由のレスポンス構造検証
- ログアウト検証
"""
from datetime import time
import unittest
from app import create_app
from database import db
from models.user import User
from models.teacher import Teacher
from models.subject import Subject
from models.classroom import Classroom
from models.time_slot import TimeSlot
from models.teacher_subject import TeacherSubject
from models.teacher_unavailability import TeacherUnavailability


class TestSystemIntegration(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SECRET_KEY': 'test-secret',
        })
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            # ユーザー作成
            admin = User(username='admin', role='admin')
            admin.set_password('adminpassword123')
            teacher_user = User(username='teacher', role='teacher', teacher_id=1)
            teacher_user.set_password('teacher123')

            t = Teacher(id=1, name='山田 太郎', employment_type='常勤', department='情報工学科', subject='')
            s = Subject(id=1, name='Python基礎', required_periods_per_week=2)
            c = Classroom(id=1, name='101教室', capacity=40, floor=1)
            slot1 = TimeSlot(id=1, period=1, floor=1, start_time=time(9, 0), end_time=time(10, 30))
            slot2 = TimeSlot(id=2, period=2, floor=1, start_time=time(10, 45), end_time=time(12, 15))

            ts = TeacherSubject(teacher_id=1, subject_id=1)

            db.session.add_all([admin, teacher_user, t, s, c, slot1, slot2, ts])
            db.session.commit()

    def test_frontend_index_serves(self):
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('Schedule Connect', html)
        self.assertIn('学校時間割・教室管理システム', html)
        self.assertNotIn('🔰 デモ受入確認の流れ', html)
        self.assertNotIn('⚡ デモ用ワンクリック入力', html)
        self.assertNotIn('Scrum Board', html)

    def test_admin_dashboard_serves(self):
        res = self.client.get('/pages/admin_dashboard.html')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('管理者ダッシュボード', html)
        self.assertIn('Schedule Connect', html)
        self.assertIn('admin_nav.js', html)

    def test_admin_nav_serves(self):
        res = self.client.get('/js/admin_nav.js')
        self.assertEqual(res.status_code, 200)
        js = res.get_data(as_text=True)
        self.assertIn('Schedule Connect', js)
        self.assertIn('handleAdminLogout', js)

    def test_teachers_html_no_old_subject_input(self):
        res = self.client.get('/pages/teachers.html')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('担当科目・勤務条件', html)
        self.assertIn('type="hidden" id="subject"', html)
        self.assertNotIn('<label for="subject">担当科目</label>', html)

    def test_teacher_settings_html(self):
        res = self.client.get('/pages/teacher_settings.html')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('担当可能科目', html)
        self.assertIn('出勤できない曜日・時限', html)
        self.assertNotIn('曜日・時限NG', html)

    def test_timetables_html_priority(self):
        res = self.client.get('/pages/timetables.html')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        # 各セクション見出しの配置順序を確認
        auto_pos = html.find('<h2>時間割を自動作成</h2>')
        cal_pos = html.find('<h2>週間カレンダー</h2>')
        manual_pos = html.find('<span id="manual-summary-title">＋ 手動で授業を追加・調整</span>')
        list_pos = html.find('<h2>時間割詳細一覧</h2>')
        self.assertTrue(0 < auto_pos < cal_pos < manual_pos < list_pos)

    def test_admin_login_and_generate(self):
        # ログイン
        res = self.client.post('/api/auth/login', json={
            'username': 'admin',
            'password': 'adminpassword123'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['user']['role'], 'admin')

        # auth/me
        me_res = self.client.get('/api/auth/me')
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.get_json()['username'], 'admin')

        # 自動生成 (201 Created)
        gen_res = self.client.post('/api/timetables/generate')
        self.assertEqual(gen_res.status_code, 201)
        gen_data = gen_res.get_json()
        self.assertEqual(gen_data['count'], 2)

        # ログアウト
        logout_res = self.client.post('/api/auth/logout')
        self.assertEqual(logout_res.status_code, 200)

        # ログアウト後のauth/me
        me_after = self.client.get('/api/auth/me')
        self.assertEqual(me_after.status_code, 401)

    def test_teacher_login_and_my_timetable(self):
        # 教員ログイン
        res = self.client.post('/api/auth/login', json={
            'username': 'teacher',
            'password': 'teacher123'
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()['user']['role'], 'teacher')

        # my/timetable
        my_res = self.client.get('/api/my/timetable')
        self.assertEqual(my_res.status_code, 200)

    def test_generate_shortage_422(self):
        # 不足条件を作って422テスト
        with self.app.app_context():
            # 教員NGを月曜〜金曜終日登録
            for d in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
                db.session.add(TeacherUnavailability(teacher_id=1, day_of_week=d, period=None))
            db.session.commit()

        self.client.post('/api/auth/login', json={'username': 'admin', 'password': 'adminpassword123'})
        gen_res = self.client.post('/api/timetables/generate')
        self.assertEqual(gen_res.status_code, 422)
        err_data = gen_res.get_json()
        self.assertIn('shortages', err_data)
        self.assertTrue(len(err_data['shortages']) > 0)


if __name__ == '__main__':
    unittest.main()
