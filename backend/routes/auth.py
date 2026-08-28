from flask import Blueprint, request, jsonify, session

from database import db
from models.user import User

auth_bp = Blueprint('auth_bp', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    if not username or not password:
        return jsonify({'error': 'username and password required'}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.is_active or not user.check_password(password):
        return jsonify({'error': 'invalid credentials'}), 401

    session.clear()
    session['user_id'] = user.id
    # do not expose password_hash in response
    u = user.to_dict()
    return jsonify({'message': 'logged in', 'user': u}), 200


@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'logged out'}), 200


@auth_bp.route('/me', methods=['GET'])
def me():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'unauthenticated'}), 401
    user = User.query.get(user_id)
    if not user:
        session.clear()
        return jsonify({'error': 'unauthenticated'}), 401
    return jsonify(user.to_dict()), 200
