import unittest

from app import create_app
from database import db
from models.user import User


class A2ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite://'})
        self.client = self.app.test_client()
        with self.app.app_context():
            admin = User(username='a2-admin', role='admin')
            admin.set_password('test-password')
            db.session.add(admin)
            db.session.commit()
        response = self.client.post('/api/auth/login', json={
            'username': 'a2-admin', 'password': 'test-password',
        })
        self.assertEqual(response.status_code, 200)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def _teacher(self, name='担当教員'):
        response = self.client.post('/api/teachers', json={'name': name})
        self.assertEqual(response.status_code, 201)
        return response.get_json()

    def _classroom(self, name='A101'):
        response = self.client.post('/api/classrooms', json={'name': name})
        self.assertEqual(response.status_code, 201)
        return response.get_json()

    def _subject(self, name='数学', periods=2):
        response = self.client.post('/api/subjects', json={
            'name': name,
            'required_periods_per_week': periods,
        })
        self.assertEqual(response.status_code, 201)
        return response.get_json()

    def _assign(self, teacher_id, subject_id):
        return self.client.post(f'/api/teachers/{teacher_id}/subjects', json={'subject_id': subject_id})

    def test_subject_crud_and_validation(self):
        subject = self._subject('数学', 2)
        self.assertEqual(self.client.get('/api/subjects').get_json(), [subject])
        self.assertEqual(self.client.get(f"/api/subjects/{subject['id']}").get_json(), subject)

        response = self.client.put(f"/api/subjects/{subject['id']}", json={
            'name': '応用数学', 'required_periods_per_week': 4,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['required_periods_per_week'], 4)

        self.assertEqual(self.client.post('/api/subjects', json={
            'name': ' ', 'required_periods_per_week': 1,
        }).status_code, 400)
        self.assertEqual(self.client.post('/api/subjects', json={
            'name': '応用数学', 'required_periods_per_week': 2,
        }).status_code, 409)
        self.assertEqual(self.client.post('/api/subjects', json={
            'name': '英語', 'required_periods_per_week': 0,
        }).status_code, 400)
        self.assertEqual(self.client.post('/api/subjects', json={
            'name': '奇数コマ科目', 'required_periods_per_week': 3,
        }).status_code, 400)
        self.assertEqual(self.client.delete(f"/api/subjects/{subject['id']}").status_code, 200)

    def test_teacher_subject_assignment_rejects_duplicates_and_missing_records(self):
        teacher = self._teacher()
        subject = self._subject()
        self.assertEqual(self._assign(teacher['id'], subject['id']).status_code, 201)
        assignments = self.client.get(f"/api/teachers/{teacher['id']}/subjects").get_json()
        self.assertEqual(assignments[0]['subject_id'], subject['id'])
        self.assertEqual(self._assign(teacher['id'], subject['id']).status_code, 409)
        self.assertEqual(self._assign(teacher['id'], 9999).status_code, 404)
        self.assertEqual(self._assign(9999, subject['id']).status_code, 404)
        self.assertEqual(self.client.delete(
            f"/api/teachers/{teacher['id']}/subjects/{subject['id']}"
        ).status_code, 200)

    def test_teacher_unavailability_supports_day_and_period_constraints(self):
        teacher = self._teacher()
        endpoint = f"/api/teachers/{teacher['id']}/unavailable-slots"
        all_day = self.client.post(endpoint, json={'day_of_week': 'Tuesday', 'period': None})
        self.assertEqual(all_day.status_code, 201)
        period = self.client.post(endpoint, json={'day_of_week': 'Thursday', 'period': 3})
        self.assertEqual(period.status_code, 201)
        self.assertEqual(len(self.client.get(endpoint).get_json()), 2)
        self.assertEqual(self.client.post(endpoint, json={'day_of_week': 'Sunday', 'period': None}).status_code, 400)
        self.assertEqual(self.client.post(endpoint, json={'day_of_week': 'Monday', 'period': 6}).status_code, 400)
        self.assertEqual(self.client.post(endpoint, json={'day_of_week': 'Thursday', 'period': 3}).status_code, 409)
        self.assertEqual(self.client.post(
            '/api/teachers/9999/unavailable-slots', json={'day_of_week': 'Monday', 'period': 1}
        ).status_code, 404)
        self.assertEqual(self.client.delete(f"{endpoint}/{period.get_json()['id']}").status_code, 200)

    def test_manual_timetable_validates_subject_assignment_unavailability_and_conflicts(self):
        teacher = self._teacher()
        other_teacher = self._teacher('別の教員')
        classroom = self._classroom()
        other_classroom = self._classroom('A102')
        subject = self._subject()
        other_subject = self._subject('英語')
        self.assertEqual(self._assign(teacher['id'], subject['id']).status_code, 201)
        self.assertEqual(self._assign(other_teacher['id'], subject['id']).status_code, 201)

        payload = {
            'day_of_week': 'Monday', 'period': 1, 'teacher_id': teacher['id'],
            'subject_id': subject['id'], 'classroom_id': classroom['id'],
        }
        created = self.client.post('/api/timetables', json=payload)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.get_json()['subject_id'], subject['id'])
        self.assertEqual(self.client.post('/api/timetables', json={
            **payload, 'subject_id': other_subject['id'], 'period': 2,
        }).status_code, 400)
        self.assertEqual(self.client.post('/api/timetables', json={
            **payload, 'classroom_id': other_classroom['id'],
        }).status_code, 409)

        self.assertEqual(self.client.post(
            f"/api/teachers/{teacher['id']}/unavailable-slots",
            json={'day_of_week': 'Tuesday', 'period': None},
        ).status_code, 201)
        self.assertEqual(self.client.post('/api/timetables', json={
            **payload, 'day_of_week': 'Tuesday', 'period': 2,
        }).status_code, 400)

        self.assertEqual(self.client.post('/api/timetables', json={
            **payload, 'teacher_id': other_teacher['id'],
        }).status_code, 409)

        # PUT uses the same validation as POST.  Each rejected request must
        # leave the original row unchanged.
        other_entry = self.client.post('/api/timetables', json={
            **payload,
            'day_of_week': 'Wednesday',
            'period': 3,
            'teacher_id': other_teacher['id'],
            'classroom_id': other_classroom['id'],
        })
        self.assertEqual(other_entry.status_code, 201)
        timetable_id = created.get_json()['id']

        self.assertEqual(self.client.put(f'/api/timetables/{timetable_id}', json={
            **payload, 'day_of_week': 'Thursday', 'period': 1, 'subject_id': other_subject['id'],
        }).status_code, 400)

        self.assertEqual(self.client.post(
            f"/api/teachers/{teacher['id']}/unavailable-slots",
            json={'day_of_week': 'Thursday', 'period': 2},
        ).status_code, 201)
        self.assertEqual(self.client.put(f'/api/timetables/{timetable_id}', json={
            **payload, 'day_of_week': 'Thursday', 'period': 2,
        }).status_code, 400)

        self.assertEqual(self.client.put(f'/api/timetables/{timetable_id}', json={
            **payload,
            'day_of_week': 'Wednesday',
            'period': 3,
            'teacher_id': other_teacher['id'],
        }).status_code, 409)
        self.assertEqual(self.client.put(f'/api/timetables/{timetable_id}', json={
            **payload,
            'day_of_week': 'Wednesday',
            'period': 3,
            'classroom_id': other_classroom['id'],
        }).status_code, 409)

        unchanged = self.client.get(f'/api/timetables/{timetable_id}').get_json()
        self.assertEqual((unchanged['day_of_week'], unchanged['period']), ('Monday', 1))


if __name__ == '__main__':
    unittest.main()
