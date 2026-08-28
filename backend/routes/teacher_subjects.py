from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError

from database import db
from models.teacher_subject import TeacherSubject
from models.teacher import Teacher
from models.subject import Subject
from utils.auth import require_admin


teacher_subjects_bp = Blueprint('teacher_subjects_bp', __name__)


@teacher_subjects_bp.route('', methods=['GET'])
@require_admin()
def list_teacher_subjects():
    items = TeacherSubject.query.all()
    return jsonify([t.to_dict() for t in items]), 200


@teacher_subjects_bp.route('', methods=['POST'])
@require_admin()
def create_teacher_subject():
    data = request.get_json(silent=True) or {}
    teacher_id = data.get('teacher_id')
    subject_id = data.get('subject_id')
    if not teacher_id or not subject_id:
        return jsonify({'error': 'teacher_id and subject_id are required'}), 400

    if not Teacher.query.get(teacher_id) or not Subject.query.get(subject_id):
        return jsonify({'error': 'teacher_id or subject_id does not exist'}), 400

    if TeacherSubject.query.filter_by(teacher_id=teacher_id, subject_id=subject_id).first():
        return jsonify({'error': 'assignment already exists'}), 409

    ts = TeacherSubject(teacher_id=teacher_id, subject_id=subject_id)
    db.session.add(ts)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'failed to create assignment'}), 500
    return jsonify(ts.to_dict()), 201


@teacher_subjects_bp.route('/<int:assignment_id>', methods=['DELETE'])
@require_admin()
def delete_teacher_subject(assignment_id):
    ts = TeacherSubject.query.get(assignment_id)
    if not ts:
        return jsonify({'error': 'not found'}), 404
    db.session.delete(ts)
    db.session.commit()
    return jsonify({'message': 'deleted'}), 200
