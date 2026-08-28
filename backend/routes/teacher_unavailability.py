from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError

from database import db
from models.teacher_unavailability import TeacherUnavailability, VALID_DAYS
from models.teacher import Teacher
from utils.auth import require_admin


teacher_unavailability_bp = Blueprint('teacher_unavailability_bp', __name__)


@teacher_unavailability_bp.route('', methods=['GET'])
@require_admin()
def list_unavailability():
    items = TeacherUnavailability.query.all()
    return jsonify([i.to_dict() for i in items]), 200


def _validate_payload(data):
    teacher_id = data.get('teacher_id')
    day = data.get('day_of_week')
    period = data.get('period', None)
    if not teacher_id or not day:
        return None, jsonify({'error': 'teacher_id and day_of_week are required'}), 400
    if day not in VALID_DAYS:
        return None, jsonify({'error': f'day_of_week must be one of {VALID_DAYS}'}), 400
    if period is not None:
        try:
            p = int(period)
        except Exception:
            return None, jsonify({'error': 'period must be an integer between 1 and 5 or null'}), 400
        if p < 1 or p > 5:
            return None, jsonify({'error': 'period must be between 1 and 5'}), 400
    return (teacher_id, day, period), None, None


@teacher_unavailability_bp.route('', methods=['POST'])
@require_admin()
def create_unavailability():
    payload, resp, status = _validate_payload(request.get_json(silent=True) or {})
    if resp:
        return resp, status
    teacher_id, day, period = payload
    if not Teacher.query.get(teacher_id):
        return jsonify({'error': 'teacher_id does not exist'}), 400

    item = TeacherUnavailability(teacher_id=teacher_id, day_of_week=day, period=period)
    db.session.add(item)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'conflict or invalid data'}), 409
    return jsonify(item.to_dict()), 201


@teacher_unavailability_bp.route('/<int:item_id>', methods=['PUT'])
@require_admin()
def update_unavailability(item_id):
    item = TeacherUnavailability.query.get(item_id)
    if not item:
        return jsonify({'error': 'not found'}), 404
    payload, resp, status = _validate_payload(request.get_json(silent=True) or {})
    if resp:
        return resp, status
    teacher_id, day, period = payload
    if not Teacher.query.get(teacher_id):
        return jsonify({'error': 'teacher_id does not exist'}), 400
    item.teacher_id = teacher_id
    item.day_of_week = day
    item.period = period
    db.session.commit()
    return jsonify(item.to_dict()), 200


@teacher_unavailability_bp.route('/<int:item_id>', methods=['DELETE'])
@require_admin()
def delete_unavailability(item_id):
    item = TeacherUnavailability.query.get(item_id)
    if not item:
        return jsonify({'error': 'not found'}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({'message': 'deleted'}), 200
