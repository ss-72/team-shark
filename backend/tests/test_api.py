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


if __name__ == '__main__':
    unittest.main()