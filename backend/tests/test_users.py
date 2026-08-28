import unittest

from app import create_app
from database import db

from models.user import User
from models.teacher import Teacher


class UsersValidationTestCase(unittest.TestCase):
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

    def _login_as_admin(self):
        with self.app.app_context():
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(username='admin', role='admin')
                admin.set_password('secret')
                db.session.add(admin)
                db.session.commit()

        resp = self.client.post('/api/auth/login', json={'username': 'admin', 'password': 'secret'})
        self.assertEqual(resp.status_code, 200)

    def test_create_user_role_validation(self):
        self._login_as_admin()
        # invalid role
        resp = self.client.post('/api/users', json={'username': 'u1', 'password': 'p', 'role': 'foo'})
        self.assertEqual(resp.status_code, 400)

    def test_create_teacher_requires_teacher_id(self):
        self._login_as_admin()
        # create teacher record
        with self.app.app_context():
            t = Teacher(name='T1')
            db.session.add(t)
            db.session.commit()
            tid = t.id

        # missing teacher_id
        resp = self.client.post('/api/users', json={'username': 'u2', 'password': 'p', 'role': 'teacher'})
        self.assertEqual(resp.status_code, 400)

        # valid teacher_id
        resp = self.client.post('/api/users', json={'username': 'u3', 'password': 'p', 'role': 'teacher', 'teacher_id': tid})
        self.assertEqual(resp.status_code, 201)

    def test_deactivate_clears_session_on_next_request(self):
        self._login_as_admin()
        # create teacher and user
        with self.app.app_context():
            t = Teacher(name='T2')
            db.session.add(t)
            db.session.commit()
            u = User(username='teachuser', role='teacher', teacher_id=t.id)
            u.set_password('pw')
            db.session.add(u)
            db.session.commit()

        # login as that user
        teacher_client = self.app.test_client()
        resp = teacher_client.post('/api/auth/login', json={'username': 'teachuser', 'password': 'pw'})
        self.assertEqual(resp.status_code, 200)

        # admin deactivates user
        self._login_as_admin()
        # find user id
        with self.app.app_context():
            uid = User.query.filter_by(username='teachuser').first().id

        resp = self.client.put(f'/api/users/{uid}', json={'is_active': False})
        self.assertEqual(resp.status_code, 200)

        # subsequent access to /api/auth/me should be unauthorized
        resp = teacher_client.get('/api/auth/me')
        self.assertEqual(resp.status_code, 401)


if __name__ == '__main__':
    unittest.main()
