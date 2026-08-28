import unittest

from app import create_app
from database import db
from models.teacher import Teacher
from models.classroom import Classroom
from models.subject import Subject
from models.teacher_subject import TeacherSubject
from models.teacher_unavailability import TeacherUnavailability
from models.user import User
from models.timetable import Timetable
from services.timetable_generator import generate_candidate_schedule


class TeamBRequirementsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite://',
            'SECRET_KEY': 'test-secret-key',
        })
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

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

    def test_generate_schedule_respects_subject_requirements_and_constraints(self):
        teacher_a = self._create_teacher('A')
        teacher_b = self._create_teacher('B')
        classroom_1 = self._create_classroom('101')
        classroom_2 = self._create_classroom('102')

        math = self._create_subject('数学', 2)
        eng = self._create_subject('英語', 1)

        db.session.add_all([
            TeacherSubject(teacher_id=teacher_a.id, subject_id=math.id),
            TeacherSubject(teacher_id=teacher_b.id, subject_id=math.id),
            TeacherSubject(teacher_id=teacher_a.id, subject_id=eng.id),
            TeacherSubject(teacher_id=teacher_b.id, subject_id=eng.id),
        ])
        db.session.add(TeacherUnavailability(teacher_id=teacher_a.id, day_of_week='Monday', period=None))
        db.session.commit()

        schedule = generate_candidate_schedule()
        counts = {}
        for item in schedule:
            counts[item['subject_id']] = counts.get(item['subject_id'], 0) + 1

        self.assertEqual(counts.get(math.id), 2)
        self.assertEqual(counts.get(eng.id), 1)

        for item in schedule:
            self.assertNotEqual(item['teacher_id'], teacher_a.id if item['day_of_week'] == 'Monday' else None)

    def test_generate_route_rejects_unsatisfiable_schedule_without_dropping_existing_data(self):
        teacher = self._create_teacher('授業担当')
        classroom = self._create_classroom('201')
        subject = self._create_subject('情報', 1)
        db.session.add(TeacherSubject(teacher_id=teacher.id, subject_id=subject.id))

        existing = Timetable(
            teacher_id=teacher.id,
            subject_id=subject.id,
            classroom_id=classroom.id,
            day_of_week='Monday',
            period=1,
        )
        db.session.add(existing)
        db.session.commit()

        response = self.client.post('/api/timetables/generate')
        self.assertEqual(response.status_code, 422)
        payload = response.get_json()
        self.assertIn('shortages', payload)
        self.assertEqual(Timetable.query.count(), 1)

    def test_my_timetable_is_limited_to_logged_in_teacher(self):
        teacher_a = self._create_teacher('自分')
        teacher_b = self._create_teacher('他人')
        classroom_1 = self._create_classroom('A101')
        classroom_2 = self._create_classroom('B201')
        subject_a = self._create_subject('国語', 1)
        subject_b = self._create_subject('数学', 1)

        db.session.add_all([
            TeacherSubject(teacher_id=teacher_a.id, subject_id=subject_a.id),
            TeacherSubject(teacher_id=teacher_b.id, subject_id=subject_b.id),
            Timetable(teacher_id=teacher_a.id, subject_id=subject_a.id, classroom_id=classroom_1.id, day_of_week='Wednesday', period=3),
            Timetable(teacher_id=teacher_b.id, subject_id=subject_b.id, classroom_id=classroom_2.id, day_of_week='Thursday', period=2),
        ])
        db.session.commit()

        user = User(username='teacher-a', password_hash='hashed', role='teacher', teacher_id=teacher_a.id, is_active=True)
        db.session.add(user)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = user.id

        response = self.client.get('/api/my/timetable')
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]['teacher_id'], teacher_a.id)
        self.assertEqual(payload[0]['classroom'], 'A101')


if __name__ == '__main__':
    unittest.main()
