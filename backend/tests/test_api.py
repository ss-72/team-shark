import unittest
import os
import tempfile

from app import create_app
from database import db


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{self.db_path}',
        })
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_teacher_crud(self):
        response = self.client.post('/api/teachers', json={
            'name': '山田太郎',
            'employment_type': '常勤',
            'department': '情報科学',
            'subject': 'Python',
        })
        self.assertEqual(response.status_code, 201)

        response = self.client.get('/api/teachers')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()), 1)

    def test_classroom_crud(self):
        response = self.client.post('/api/classrooms', json={
            'name': 'A101',
            'capacity': 40,
            'floor': 1,
            'priority_department': '情報科学',
        })
        self.assertEqual(response.status_code, 201)

        response = self.client.get('/api/classrooms')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()), 1)

    def test_time_slots_seeded_and_accessible(self):
        response = self.client.get('/api/time_slots')
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(len(payload), 6)
        self.assertTrue(any(item['floor'] == 3 and item['period'] == 3 for item in payload))


    def test_generate_timetable_assigns_part_time_teacher(self):
        response = self.client.post('/api/teachers', json={
            'name': '田中 花子',
            'employment_type': '常勤',
            'department': '国語',
            'subject': '国語',
        })
        self.assertEqual(response.status_code, 201)
        full_time_teacher = response.get_json()

        response = self.client.post('/api/teachers', json={
            'name': '鈴木 一郎',
            'employment_type': '非常勤',
            'department': '体育',
            'subject': '体育',
        })
        self.assertEqual(response.status_code, 201)
        part_time_teacher = response.get_json()

        response = self.client.post('/api/classrooms', json={
            'name': 'B201',
            'capacity': 30,
            'floor': 2,
            'priority_department': '体育',
        })
        self.assertEqual(response.status_code, 201)
        classroom = response.get_json()

        response = self.client.post('/api/timetables/generate')
        self.assertEqual(response.status_code, 201)
        payload = response.get_json()
        self.assertEqual(payload['count'], 2)

        timetable_teacher_ids = {item['teacher_id'] for item in payload['timetables']}
        self.assertEqual(timetable_teacher_ids, {full_time_teacher['id'], part_time_teacher['id']})

        part_time_entries = [item for item in payload['timetables'] if item['teacher_id'] == part_time_teacher['id']]
        self.assertEqual(len(part_time_entries), 1)
        self.assertEqual(part_time_entries[0]['classroom_id'], classroom['id'])


if __name__ == '__main__':
    unittest.main()