import unittest

from app import create_app
from database import db
from models.user import User


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite://',
        })
        self.client = self.app.test_client()
        with self.app.app_context():
            admin = User(username='test-admin', role='admin')
            admin.set_password('test-password')
            db.session.add(admin)
            db.session.commit()
        response = self.client.post('/api/auth/login', json={
            'username': 'test-admin', 'password': 'test-password',
        })
        self.assertEqual(response.status_code, 200)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def _create_teacher(self, name, employment_type='常勤'):
        response = self.client.post('/api/teachers', json={
            'name': name,
            'employment_type': employment_type,
            'department': '情報科学',
            'subject': 'Python',
        })
        self.assertEqual(response.status_code, 201)
        return response.get_json()

    def _create_classroom(self, name):
        response = self.client.post('/api/classrooms', json={
            'name': name,
            'capacity': 40,
            'floor': 1,
            'priority_department': '情報科学',
        })
        self.assertEqual(response.status_code, 201)
        return response.get_json()

    def _create_subject(self, name, required_periods_per_week=1):
        response = self.client.post('/api/subjects', json={
            'name': name,
            'required_periods_per_week': required_periods_per_week,
        })
        self.assertEqual(response.status_code, 201)
        return response.get_json()

    def _assign_subject(self, teacher_id, subject_id):
        response = self.client.post(f'/api/teachers/{teacher_id}/subjects', json={
            'subject_id': subject_id,
        })
        self.assertEqual(response.status_code, 201)

    def test_testing_mode_does_not_seed_development_data(self):
        self.assertEqual(self.client.get('/api/teachers').get_json(), [])
        self.assertEqual(self.client.get('/api/classrooms').get_json(), [])
        self.assertEqual(self.client.get('/api/time_slots').get_json(), [])

    def test_teacher_crud(self):
        teacher = self._create_teacher('山田太郎')

        response = self.client.get('/api/teachers')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()), 1)

        response = self.client.put(f"/api/teachers/{teacher['id']}", json={
            'name': '山田次郎',
            'employment_type': '非常勤',
            'department': '情報科学',
            'subject': 'Python',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['name'], '山田次郎')

        response = self.client.delete(f"/api/teachers/{teacher['id']}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/api/teachers').get_json(), [])

    def test_classroom_crud(self):
        classroom = self._create_classroom('A101')

        response = self.client.get('/api/classrooms')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()), 1)

        response = self.client.put(f"/api/classrooms/{classroom['id']}", json={
            'name': 'A102',
            'capacity': 45,
            'floor': 1,
            'priority_department': '情報科学',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['name'], 'A102')

        response = self.client.delete(f"/api/classrooms/{classroom['id']}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/api/classrooms').get_json(), [])

    def test_time_slot_crud(self):
        response = self.client.post('/api/time_slots', json={
            'period': 1,
            'start_time': '09:00',
            'end_time': '10:30',
        })
        self.assertEqual(response.status_code, 201)
        time_slot = response.get_json()

        response = self.client.get('/api/time_slots')
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]['period'], 1)

        response = self.client.put(f"/api/time_slots/{time_slot['id']}", json={
            'period': 2,
            'start_time': '10:45',
            'end_time': '12:15',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['period'], 2)

        response = self.client.delete(f"/api/time_slots/{time_slot['id']}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/api/time_slots').get_json(), [])

    def test_timetable_crud(self):
        teacher = self._create_teacher('田中 花子')
        classroom = self._create_classroom('B201')
        subject = self._create_subject('Python')
        self._assign_subject(teacher['id'], subject['id'])

        response = self.client.post('/api/timetables', json={
            'day_of_week': 'Monday',
            'period': 1,
            'teacher_id': teacher['id'],
            'subject_id': subject['id'],
            'classroom_id': classroom['id'],
        })
        self.assertEqual(response.status_code, 201)
        timetable = response.get_json()

        response = self.client.get('/api/timetables')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()), 1)

        response = self.client.put(f"/api/timetables/{timetable['id']}", json={
            'day_of_week': 'Tuesday',
            'period': 2,
            'teacher_id': teacher['id'],
            'subject_id': subject['id'],
            'classroom_id': classroom['id'],
            'is_online': True,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['day_of_week'], 'Tuesday')

        response = self.client.delete(f"/api/timetables/{timetable['id']}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/api/timetables').get_json(), [])


if __name__ == '__main__':
    unittest.main()
