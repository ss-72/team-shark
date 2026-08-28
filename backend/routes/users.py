from flask import Blueprint, request, jsonify, session
from sqlalchemy.exc import IntegrityError

from database import db
from models.user import User
from models.teacher import Teacher
from utils.auth import require_admin

users_bp = Blueprint('users_bp', __name__)


@users_bp.route('', methods=['GET'])
@require_admin()
def list_users():
    users = User.query.all()
    return jsonify([u.to_dict() for u in users]), 200


@users_bp.route('', methods=['POST'])
@require_admin()
def create_user():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    role = (data.get('role') or 'teacher')
    teacher_id = data.get('teacher_id')

    if not username or not password:
        return jsonify({'error': 'username and password required'}), 400
    if role not in ('admin', 'teacher'):
        return jsonify({'error': 'role must be admin or teacher'}), 400
    if role == 'teacher':
        if teacher_id is None or not Teacher.query.get(teacher_id):
            return jsonify({'error': 'teacher_id must reference an existing Teacher for teacher role'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'username already exists'}), 409

    user = User(username=username, role=role, teacher_id=teacher_id)
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'failed to create user'}), 500
    return jsonify(user.to_dict()), 201


@users_bp.route('/<int:user_id>', methods=['GET'])
@require_admin()
def get_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'not found'}), 404
    return jsonify(user.to_dict()), 200


@users_bp.route('/<int:user_id>', methods=['PUT'])
@require_admin()
def update_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'not found'}), 404

    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    role = data.get('role')
    is_active = data.get('is_active')

    if username:
        if User.query.filter(User.username == username, User.id != user_id).first():
            return jsonify({'error': 'username already exists'}), 409
        user.username = username
    if role:
        if role not in ('admin', 'teacher'):
            return jsonify({'error': 'role must be admin or teacher'}), 400
        user.role = role
    if is_active is not None:
        # If deactivating, clear session info is handled in before_request checks
        user.is_active = bool(is_active)

    if data.get('password'):
        user.set_password(data.get('password'))

    db.session.commit()
    return jsonify(user.to_dict()), 200


@users_bp.route('/<int:user_id>', methods=['DELETE'])
@require_admin()
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'not found'}), 404
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'deleted'}), 200
