from functools import wraps
from flask import session, jsonify, g

from database import db
from models.user import User


def current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    user = User.query.get(user_id)
    return user


def require_auth():
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                return jsonify({'error': 'unauthenticated'}), 401
            if not user.is_active:
                return jsonify({'error': 'user inactive'}), 401
            g.current_user = user
            return f(*args, **kwargs)
        return wrapped
    return decorator


def require_admin():
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                return jsonify({'error': 'unauthenticated'}), 401
            if not user.is_active:
                return jsonify({'error': 'user inactive'}), 401
            if user.role != 'admin':
                return jsonify({'error': 'forbidden'}), 403
            g.current_user = user
            return f(*args, **kwargs)
        return wrapped
    return decorator


def register_request_checks(app):
    @app.before_request
    def _check_session_user_active():
        # Ensure any session-bound user still exists and is active on each request
        user_id = session.get('user_id')
        if not user_id:
            return None
        user = User.query.get(user_id)
        if not user or not user.is_active:
            session.clear()
            # Returning None continues request; decorators will return 401 when needed
        return None
