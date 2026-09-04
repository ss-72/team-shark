from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from database import db
from models.subject import KOMAS_PER_PERIOD, Subject
from models.teacher_subject import TeacherSubject
from models.timetable import Timetable
from utils.auth import require_admin


subjects_bp = Blueprint('subjects_bp', __name__)
VALID_GRADES = (2, 3, 4)


def _validated_subject_payload(data, default_grade=2):
    raw_name = data.get('name')
    name = raw_name.strip() if isinstance(raw_name, str) else ''
    if not name:
        return None, jsonify({'error': '科目名 (name) は必須です'}), 400

    required_periods = data.get('required_periods_per_week')
    if (
        isinstance(required_periods, bool)
        or not isinstance(required_periods, int)
        or required_periods < KOMAS_PER_PERIOD
        or required_periods % KOMAS_PER_PERIOD != 0
    ):
        return None, jsonify({'error': '必要コマ数は2以上の偶数で指定してください（1時限＝2コマ）'}), 400
    grade = data.get('grade', default_grade)
    if isinstance(grade, bool) or not isinstance(grade, int) or grade not in VALID_GRADES:
        return None, jsonify({'error': 'grade must be 2, 3, or 4'}), 400
    return (name, required_periods, grade), None, None


def _subject_name_exists(name, exclude_id=None):
    query = Subject.query.filter(db.func.lower(Subject.name) == name.lower())
    if exclude_id is not None:
        query = query.filter(Subject.id != exclude_id)
    return query.first() is not None


@subjects_bp.route('', methods=['GET'])
def get_subjects():
    return jsonify([subject.to_dict() for subject in Subject.query.order_by(Subject.id).all()]), 200


@subjects_bp.route('', methods=['POST'])
@require_admin()
def create_subject():
    payload, response, status = _validated_subject_payload(request.get_json(silent=True) or {})
    if response:
        return response, status
    name, required_periods, grade = payload
    if _subject_name_exists(name):
        return jsonify({'error': f'科目名「{name}」は既に登録されています'}), 409

    subject = Subject(name=name, required_periods_per_week=required_periods, grade=grade)
    db.session.add(subject)
    db.session.commit()
    return jsonify(subject.to_dict()), 201


@subjects_bp.route('/<int:subject_id>', methods=['GET'])
def get_subject(subject_id):
    subject = db.session.get(Subject, subject_id)
    if not subject:
        return jsonify({'error': '該当する科目が見つかりません'}), 404
    return jsonify(subject.to_dict()), 200


@subjects_bp.route('/<int:subject_id>', methods=['PUT'])
@require_admin()
def update_subject(subject_id):
    subject = db.session.get(Subject, subject_id)
    if not subject:
        return jsonify({'error': '該当する科目が見つかりません'}), 404
    payload, response, status = _validated_subject_payload(
        request.get_json(silent=True) or {}, default_grade=subject.grade
    )
    if response:
        return response, status
    name, required_periods, grade = payload
    if _subject_name_exists(name, exclude_id=subject.id):
        return jsonify({'error': f'科目名「{name}」は既に登録されています'}), 409

    if grade != subject.grade:
        for entry in Timetable.query.filter_by(subject_id=subject.id).all():
            conflict = Timetable.query.join(Subject, Timetable.subject_id == Subject.id).filter(
                Timetable.id != entry.id,
                Timetable.day_of_week == entry.day_of_week,
                Timetable.period == entry.period,
                Subject.grade == grade,
            ).first()
            if conflict:
                return jsonify({'error': 'Changing this grade would overlap classes for the same grade'}), 409

    subject.name = name
    subject.required_periods_per_week = required_periods
    subject.grade = grade
    db.session.commit()
    return jsonify(subject.to_dict()), 200


@subjects_bp.route('/<int:subject_id>', methods=['DELETE'])
@require_admin()
def delete_subject(subject_id):
    subject = db.session.get(Subject, subject_id)
    if not subject:
        return jsonify({'error': '該当する科目が見つかりません'}), 404
    if TeacherSubject.query.filter_by(subject_id=subject.id).first() or Timetable.query.filter_by(subject_id=subject.id).first():
        return jsonify({'error': '担当教員または時間割から参照されている科目は削除できません'}), 409

    db.session.delete(subject)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': '参照されている科目は削除できません'}), 409
    return jsonify({'message': f'科目ID {subject_id} を削除しました'}), 200
