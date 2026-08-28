import unittest

from app import create_app
from database import db

from models.user import User
from models.teacher import Teacher


class AuthAdminExtraTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite://',
        })
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_login_failure_bad_credentials(self):
        with self.app.app_context():
            u = User(username='u1', role='teacher')
            u.set_password('correct')
            db.session.add(u)
            db.session.commit()

        resp = self.client.post('/api/auth/login', json={'username': 'u1', 'password': 'wrong'})
        self.assertEqual(resp.status_code, 401)

    def test_inactive_user_cannot_login(self):
        with self.app.app_context():
            u = User(username='inactive', role='teacher', is_active=False)
            u.set_password('pw')
            db.session.add(u)
            db.session.commit()

        resp = self.client.post('/api/auth/login', json={'username': 'inactive', 'password': 'pw'})
        self.assertEqual(resp.status_code, 401)

    def test_non_admin_forbidden_on_admin_endpoints(self):
        with self.app.app_context():
            # create teacher record
            t = Teacher(name='T1')
            db.session.add(t)
            db.session.commit()
            # create non-admin user
            u = User(username='teacheruser', role='teacher', teacher_id=t.id)
            u.set_password('pw')
            db.session.add(u)
            db.session.commit()

        # login as non-admin
        resp = self.client.post('/api/auth/login', json={'username': 'teacheruser', 'password': 'pw'})
        self.assertEqual(resp.status_code, 200)

        # attempt admin action
        resp = self.client.post('/api/subjects', json={'name': 'NewSub', 'required_periods_per_week': 2})
        self.assertIn(resp.status_code, (401, 403))

    def test_password_not_exposed_in_responses(self):
        with self.app.app_context():
            admin = User(username='admin', role='admin')
            admin.set_password('secret')
            db.session.add(admin)
            db.session.commit()

        resp = self.client.post('/api/auth/login', json={'username': 'admin', 'password': 'secret'})
        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        self.assertIn('user', payload)
        self.assertNotIn('password_hash', payload['user'])

    def test_user_input_validation_on_create(self):
        # create admin to perform actions
        with self.app.app_context():
            admin = User(username='admin2', role='admin')
            admin.set_password('secret')
            db.session.add(admin)
            db.session.commit()
        self.client.post('/api/auth/login', json={'username': 'admin2', 'password': 'secret'})

        # invalid role
        resp = self.client.post('/api/users', json={'username': 'x', 'password': 'p', 'role': 'invalid'})
        self.assertEqual(resp.status_code, 400)

        # teacher role requires valid teacher_id
        resp = self.client.post('/api/users', json={'username': 'x2', 'password': 'p', 'role': 'teacher'})
        self.assertEqual(resp.status_code, 400)


if __name__ == '__main__':
    unittest.main()
