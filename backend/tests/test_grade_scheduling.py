import unittest

from app import create_app
from database import db
from models.classroom import Classroom
from models.subject import Subject
from models.teacher import Teacher
from models.teacher_subject import TeacherSubject
from services.timetable_generator import generate_candidate_schedule, validate_schedule


class GradeSchedulingTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite://',
            'SECRET_KEY': 'test-secret',
        })
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_same_grade_never_shares_a_slot_but_different_grades_can(self):
        teacher_one = Teacher(name='Teacher one')
        teacher_two = Teacher(name='Teacher two')
        room_one = Classroom(name='Room one', capacity=20, floor=1)
        room_two = Classroom(name='Room two', capacity=20, floor=1)
        grade_two_a = Subject(name='Grade two A', required_periods_per_week=2, grade=2)
        grade_two_b = Subject(name='Grade two B', required_periods_per_week=2, grade=2)
        db.session.add_all([
            teacher_one, teacher_two, room_one, room_two, grade_two_a, grade_two_b,
        ])
        db.session.commit()
        db.session.add_all([
            TeacherSubject(teacher_id=teacher_one.id, subject_id=grade_two_a.id),
            TeacherSubject(teacher_id=teacher_two.id, subject_id=grade_two_b.id),
        ])
        db.session.commit()

        schedule = generate_candidate_schedule()
        grade_slots = [(entry['day_of_week'], entry['period'], entry['grade']) for entry in schedule]
        self.assertEqual(len(grade_slots), len(set(grade_slots)))

        same_slot = [
            {
                'subject_id': grade_two_a.id,
                'teacher_id': teacher_one.id,
                'classroom_id': room_one.id,
                'day_of_week': 'Monday',
                'period': 1,
            },
            {
                'subject_id': grade_two_b.id,
                'teacher_id': teacher_two.id,
                'classroom_id': room_two.id,
                'day_of_week': 'Monday',
                'period': 1,
            },
        ]
        self.assertFalse(validate_schedule(same_slot)[0])

        grade_two_b.grade = 3
        db.session.commit()
        self.assertTrue(validate_schedule(same_slot)[0])


if __name__ == '__main__':
    unittest.main()
