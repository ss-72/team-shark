import unittest
from unittest.mock import patch

from app import create_app
from database import db
from models.teacher import Teacher
from models.classroom import Classroom
from models.subject import Subject
from models.teacher_subject import TeacherSubject
from models.teacher_unavailability import TeacherUnavailability
from models.user import User
from models.timetable import Timetable
from services.timetable_generator import (
    generate_candidate_schedule,
    generate_timetable,
    validate_schedule,
    TimetableGenerationError,
)


class TeamBRequirementsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite://',
            'SECRET_KEY': 'test-secret-key',
        })
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _create_teacher(self, name, employment_type='常勤'):
        teacher = Teacher(name=name, employment_type=employment_type)
        db.session.add(teacher)
        db.session.commit()
        return teacher

    def _create_classroom(self, name):
        classroom = Classroom(name=name, capacity=40, floor=1, priority_department='情報科学')
        db.session.add(classroom)
        db.session.commit()
        return classroom

    def _create_subject(self, name, required_periods):
        subject = Subject(name=name, required_periods_per_week=required_periods)
        db.session.add(subject)
        db.session.commit()
        return subject

    def _create_admin(self, username='admin_test'):
        admin = User(username=username, role='admin', is_active=True)
        admin.set_password('password123')
        db.session.add(admin)
        db.session.commit()
        return admin

    def _login_as(self, user):
        with self.client.session_transaction() as sess:
            sess['user_id'] = user.id

    def test_requirement_A_exact_periods_count(self):
        """A. X=3、Y=2なら生成結果もX=3、Y=2 (assigned == required)"""
        teacher_x = self._create_teacher('教員X')
        teacher_y = self._create_teacher('教員Y')
        classroom = self._create_classroom('101')

        subj_x = self._create_subject('科目X', 3)
        subj_y = self._create_subject('科目Y', 2)

        db.session.add_all([
            TeacherSubject(teacher_id=teacher_x.id, subject_id=subj_x.id),
            TeacherSubject(teacher_id=teacher_y.id, subject_id=subj_y.id),
        ])
        db.session.commit()

        schedule = generate_candidate_schedule()
        counts = {}
        for item in schedule:
            counts[item['subject_id']] = counts.get(item['subject_id'], 0) + 1

        self.assertEqual(counts.get(subj_x.id), 3)
        self.assertEqual(counts.get(subj_y.id), 2)
        self.assertEqual(len(schedule), 5)

    def test_requirement_B_only_assigned_teachers(self):
        """B. 担当外教員を割り当てない"""
        teacher_a = self._create_teacher('教員A')
        teacher_b = self._create_teacher('教員B')
        classroom = self._create_classroom('101')

        subject = self._create_subject('科目A', 2)

        # teacher_a だけが subject を担当可能
        db.session.add(TeacherSubject(teacher_id=teacher_a.id, subject_id=subject.id))
        db.session.commit()

        schedule = generate_candidate_schedule()
        self.assertEqual(len(schedule), 2)
        for item in schedule:
            self.assertEqual(item['teacher_id'], teacher_a.id)
            self.assertNotEqual(item['teacher_id'], teacher_b.id)

    def test_requirement_C_and_D_unavailability_constraints(self):
        """C. Tuesday / NULL を守る, D. Thursday / 3 を守る"""
        teacher = self._create_teacher('制約教員')
        classroom = self._create_classroom('101')
        subject = self._create_subject('必須科目', 5)

        db.session.add(TeacherSubject(teacher_id=teacher.id, subject_id=subject.id))
        # 火曜終日NG
        db.session.add(TeacherUnavailability(teacher_id=teacher.id, day_of_week='Tuesday', period=None))
        # 木曜3限NG
        db.session.add(TeacherUnavailability(teacher_id=teacher.id, day_of_week='Thursday', period=3))
        db.session.commit()

        schedule = generate_candidate_schedule()
        self.assertEqual(len(schedule), 5)
        for item in schedule:
            # 火曜日に割当がないこと
            self.assertNotEqual(item['day_of_week'], 'Tuesday')
            # 木曜3限に割当がないこと
            if item['day_of_week'] == 'Thursday':
                self.assertNotEqual(item['period'], 3)

    def test_requirement_E_and_F_no_conflicts(self):
        """E. 同一教員の同時刻重複なし, F. 同一教室の同時刻重複なし"""
        teacher_1 = self._create_teacher('教員1')
        teacher_2 = self._create_teacher('教員2')
        classroom_1 = self._create_classroom('101')
        classroom_2 = self._create_classroom('102')

        subj_1 = self._create_subject('科目1', 4)
        subj_2 = self._create_subject('科目2', 4)

        db.session.add_all([
            TeacherSubject(teacher_id=teacher_1.id, subject_id=subj_1.id),
            TeacherSubject(teacher_id=teacher_2.id, subject_id=subj_2.id),
        ])
        db.session.commit()

        schedule = generate_candidate_schedule()
        teacher_slots = set()
        classroom_slots = set()

        for item in schedule:
            t_slot = (item['day_of_week'], item['period'], item['teacher_id'])
            c_slot = (item['day_of_week'], item['period'], item['classroom_id'])

            self.assertNotIn(t_slot, teacher_slots)
            self.assertNotIn(c_slot, classroom_slots)

            teacher_slots.add(t_slot)
            classroom_slots.add(c_slot)

    def test_requirement_G_parallel_sessions(self):
        """G. 異なる教員・教室なら同一時限の並行授業可能"""
        teacher_1 = self._create_teacher('教員1')
        teacher_2 = self._create_teacher('教員2')
        classroom_1 = self._create_classroom('101')
        classroom_2 = self._create_classroom('102')

        # 5日×5限 = 25コマ。教員1は月曜1限のみ可能、教員2も月曜1限のみ可能に設定
        # 異なる教室で並行配置できるはず
        subj_1 = self._create_subject('並行1', 1)
        subj_2 = self._create_subject('並行2', 1)

        db.session.add_all([
            TeacherSubject(teacher_id=teacher_1.id, subject_id=subj_1.id),
            TeacherSubject(teacher_id=teacher_2.id, subject_id=subj_2.id),
        ])
        # 月曜1限以外をすべてNGに設定して並行配置を強制
        for day in ['Tuesday', 'Wednesday', 'Thursday', 'Friday']:
            db.session.add(TeacherUnavailability(teacher_id=teacher_1.id, day_of_week=day, period=None))
            db.session.add(TeacherUnavailability(teacher_id=teacher_2.id, day_of_week=day, period=None))
        for p in [2, 3, 4, 5]:
            db.session.add(TeacherUnavailability(teacher_id=teacher_1.id, day_of_week='Monday', period=p))
            db.session.add(TeacherUnavailability(teacher_id=teacher_2.id, day_of_week='Monday', period=p))
        db.session.commit()

        schedule = generate_candidate_schedule()
        self.assertEqual(len(schedule), 2)
        # 両方月曜1限に配置され、教室が異なっていること
        self.assertEqual(schedule[0]['day_of_week'], 'Monday')
        self.assertEqual(schedule[0]['period'], 1)
        self.assertEqual(schedule[1]['day_of_week'], 'Monday')
        self.assertEqual(schedule[1]['period'], 1)
        self.assertNotEqual(schedule[0]['classroom_id'], schedule[1]['classroom_id'])

    def test_requirement_H_and_I_generation_failure_422_and_preserves_existing(self):
        """H. 生成不能で422と不足理由, I. 生成不能後も既存Timetable保持"""
        admin = self._create_admin()
        self._login_as(admin)

        teacher = self._create_teacher('担当教員')
        classroom = self._create_classroom('201')
        subject = self._create_subject('配置不能科目', 1)

        # 担当可能教員をあえて登録しない -> 生成不能
        # 既存の時間割を用意
        existing_subject = self._create_subject('既存科目', 1)
        db.session.add(TeacherSubject(teacher_id=teacher.id, subject_id=existing_subject.id))
        existing_tt = Timetable(
            teacher_id=teacher.id,
            subject_id=existing_subject.id,
            classroom_id=classroom.id,
            day_of_week='Monday',
            period=1,
        )
        db.session.add(existing_tt)
        db.session.commit()

        # 生成APIを叩く
        response = self.client.post('/api/timetables/generate')
        self.assertEqual(response.status_code, 422)

        payload = response.get_json()
        self.assertEqual(payload.get('error'), 'timetable_generation_failed')
        self.assertIn('shortages', payload)
        shortages = payload['shortages']
        self.assertTrue(any(s['subject_id'] == subject.id for s in shortages))
        shortage = next(s for s in shortages if s['subject_id'] == subject.id)
        self.assertEqual(shortage['required'], 1)
        self.assertEqual(shortage['assigned'], 0)
        self.assertEqual(shortage['missing'], 1)
        self.assertIn('reason', shortage)
        self.assertEqual(shortage['subject_name'], '配置不能科目')

        # I. 生成不能後も既存の時間割が消えずに残っていること
        timetables = Timetable.query.all()
        self.assertEqual(len(timetables), 1)
        self.assertEqual(timetables[0].subject_id, existing_subject.id)

    def test_requirement_J_save_failure_preserves_existing(self):
        """J. DB保存失敗後も既存Timetable保持 (ロールバック確認)"""
        teacher = self._create_teacher('教員')
        classroom = self._create_classroom('101')
        subject = self._create_subject('科目', 1)
        db.session.add(TeacherSubject(teacher_id=teacher.id, subject_id=subject.id))

        existing = Timetable(
            teacher_id=teacher.id,
            subject_id=subject.id,
            classroom_id=classroom.id,
            day_of_week='Friday',
            period=5,
        )
        db.session.add(existing)
        db.session.commit()
        existing_id = existing.id

        # db.session.commit で意図的に例外を発生させる
        with patch('services.timetable_generator.db.session.commit', side_effect=RuntimeError('Simulated DB error')):
            with self.assertRaises(RuntimeError):
                generate_timetable()

        # ロールバックされ、既存の時間割が保持されていること
        remaining = Timetable.query.all()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].id, existing_id)
        self.assertEqual(remaining[0].day_of_week, 'Friday')

    def test_my_timetable_auth_and_isolation(self):
        """教員本人用時間割APIの認証・権限・他者分離テスト"""
        teacher_a = self._create_teacher('教員A')
        teacher_b = self._create_teacher('教員B')
        classroom_1 = self._create_classroom('101')
        classroom_2 = self._create_classroom('102')

        subj_a = self._create_subject('Python基礎', 2)
        subj_b = self._create_subject('ネットワーク', 1)

        db.session.add_all([
            TeacherSubject(teacher_id=teacher_a.id, subject_id=subj_a.id),
            TeacherSubject(teacher_id=teacher_b.id, subject_id=subj_b.id),
            Timetable(teacher_id=teacher_a.id, subject_id=subj_a.id, classroom_id=classroom_1.id, day_of_week='Wednesday', period=3),
            Timetable(teacher_id=teacher_a.id, subject_id=subj_a.id, classroom_id=classroom_1.id, day_of_week='Monday', period=1),
            Timetable(teacher_id=teacher_b.id, subject_id=subj_b.id, classroom_id=classroom_2.id, day_of_week='Thursday', period=2),
        ])
        db.session.commit()

        # 1. 未ログインなら 401
        res_unauth = self.client.get('/api/my/timetable')
        self.assertEqual(res_unauth.status_code, 401)

        # 2. adminなら 403
        admin = self._create_admin('admin_user')
        self._login_as(admin)
        res_admin = self.client.get('/api/my/timetable')
        self.assertEqual(res_admin.status_code, 403)

        # 3. teacher_idのない教員ユーザーなら 400
        user_no_teacher = User(username='no_teacher_user', role='teacher', teacher_id=None, is_active=True)
        user_no_teacher.set_password('pass')
        db.session.add(user_no_teacher)
        db.session.commit()
        self._login_as(user_no_teacher)
        res_no_tid = self.client.get('/api/my/timetable')
        self.assertEqual(res_no_tid.status_code, 400)

        # 4. teacher Aでログイン -> A本人の時間割のみ取得でき、Bのものは含まれない
        user_a = User(username='teacher_a_user', role='teacher', teacher_id=teacher_a.id, is_active=True)
        user_a.set_password('pass')
        db.session.add(user_a)
        db.session.commit()
        self._login_as(user_a)

        res_a = self.client.get('/api/my/timetable')
        self.assertEqual(res_a.status_code, 200)
        items = res_a.get_json()
        self.assertEqual(len(items), 2)
        # 曜日・時限順にソートされていること（Monday 1限 が先、Wednesday 3限 が次）
        self.assertEqual(items[0]['day_of_week'], 'Monday')
        self.assertEqual(items[0]['period'], 1)
        self.assertEqual(items[0]['subject'], 'Python基礎')
        self.assertEqual(items[0]['classroom'], '101')
        self.assertEqual(items[0]['teacher_id'], teacher_a.id)

        self.assertEqual(items[1]['day_of_week'], 'Wednesday')
        self.assertEqual(items[1]['period'], 3)

        # 5. クライアントから ?teacher_id=999 や teacher_b.id を送っても無視されること
        res_spoof = self.client.get(f'/api/my/timetable?teacher_id={teacher_b.id}')
        self.assertEqual(res_spoof.status_code, 200)
        spoof_items = res_spoof.get_json()
        self.assertEqual(len(spoof_items), 2)
        for it in spoof_items:
            self.assertEqual(it['teacher_id'], teacher_a.id)


if __name__ == '__main__':
    unittest.main()
