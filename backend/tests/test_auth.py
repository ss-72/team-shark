import unittest

from app import create_app
from database import db

from models.user import User


class AuthTestCase(unittest.TestCase):
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

    def test_login_me_logout_and_admin_protection(self):
        with self.app.app_context():
            # create an admin user directly
            admin = User(username='admin', role='admin')
            admin.set_password('secret')
            db.session.add(admin)
            db.session.commit()

        # login with correct credentials
        resp = self.client.post('/api/auth/login', json={'username': 'admin', 'password': 'secret'})
        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        self.assertIn('user', payload)

        # me should return the logged-in user
        resp = self.client.get('/api/auth/me')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['username'], 'admin')

        # admin-only endpoint should be accessible
        resp = self.client.get('/api/users')
        self.assertEqual(resp.status_code, 200)

        # logout
        resp = self.client.post('/api/auth/logout')
        self.assertEqual(resp.status_code, 200)

        # now /api/auth/me should be unauthorized
        resp = self.client.get('/api/auth/me')
        self.assertEqual(resp.status_code, 401)


if __name__ == '__main__':
    unittest.main()
