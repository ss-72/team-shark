from flask import Blueprint, jsonify, request

from database import db
from models.teacher import Teacher
from models.subject import Subject
from models.teacher_subject import TeacherSubject
from models.teacher_unavailability import TeacherUnavailability, VALID_DAYS
from utils.auth import require_admin

# 教員関連の API をまとめた Blueprint
teachers_bp = Blueprint('teachers_bp', __name__)


@teachers_bp.route('', methods=['GET'])
def get_teachers():
    #全教員を取得して JSON で返すエンドポイント
    teachers = Teacher.query.all()
    return jsonify([teacher.to_dict() for teacher in teachers]), 200


@teachers_bp.route('', methods=['POST'])
def create_teacher():
    #新しい教員を作成するエンドポイント#
    data = request.get_json(silent=True) or {}

    # 入力値として name が存在し、空白ではないことを確認
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({"error": "教員名 (name) は必須です"}), 400

    # 名前の重複を防止
    if _teacher_name_exists(name):
        return jsonify({"error": f"教員名「{name}」は既に登録されています"}), 409

    # 新しい Teacher インスタンスを作成して DB に追加
    teacher = Teacher(
        name=name,
        employment_type=data.get('employment_type'),
        department=data.get('department'),
        subject=data.get('subject'),
    )
    db.session.add(teacher)
    db.session.commit()
    return jsonify({**teacher.to_dict(), "message": "教員を登録しました"}), 201


@teachers_bp.route('/<int:teacher_id>', methods=['GET'])
def get_teacher(teacher_id):
    #指定 ID の教員を取得するエンドポイント
    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        return jsonify({"error": "該当する教員が見つかりません"}), 404
    return jsonify(teacher.to_dict()), 200


@teachers_bp.route('/<int:teacher_id>', methods=['PUT'])
def update_teacher(teacher_id):
    #既存の教員を更新するエンドポイント
    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        return jsonify({"error": "該当する教員が見つかりません"}), 404

    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({"error": "教員名 (name) は必須です"}), 400

    # 自分自身以外に同じ名前の教員がいないか確認
    if _teacher_name_exists(name, exclude_id=teacher_id):
        return jsonify({"error": f"教員名「{name}」は既に登録されています"}), 409

    # 教員データを更新して保存
    teacher.name = name
    teacher.employment_type = data.get('employment_type')
    teacher.department = data.get('department')
    teacher.subject = data.get('subject')

    db.session.commit()
    return jsonify({**teacher.to_dict(), "message": "教員情報を更新しました"}), 200


@teachers_bp.route('/<int:teacher_id>', methods=['DELETE'])
def delete_teacher(teacher_id):
    #指定 ID の教員を削除するエンドポイント
    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        return jsonify({"error": "該当する教員が見つかりません"}), 404

    db.session.delete(teacher)
    db.session.commit()
    return jsonify({"message": f"教員ID {teacher_id} を削除しました"}), 200


@teachers_bp.route('/<int:teacher_id>/subjects', methods=['GET'])
@require_admin()
def get_teacher_subjects(teacher_id):
    teacher = db.session.get(Teacher, teacher_id)
    if not teacher:
        return jsonify({'error': '該当する教員が見つかりません'}), 404
    assignments = TeacherSubject.query.filter_by(teacher_id=teacher.id).order_by(TeacherSubject.id).all()
    return jsonify([assignment.to_dict() for assignment in assignments]), 200


@teachers_bp.route('/<int:teacher_id>/subjects', methods=['POST'])
@require_admin()
def add_teacher_subject(teacher_id):
    teacher = db.session.get(Teacher, teacher_id)
    if not teacher:
        return jsonify({'error': '該当する教員が見つかりません'}), 404
    data = request.get_json(silent=True) or {}
    subject_id = data.get('subject_id')
    if isinstance(subject_id, bool) or not isinstance(subject_id, int):
        return jsonify({'error': 'subject_id は整数で指定してください'}), 400
    if not db.session.get(Subject, subject_id):
        return jsonify({'error': '指定された科目IDが存在しません'}), 404
    if TeacherSubject.query.filter_by(teacher_id=teacher.id, subject_id=subject_id).first():
        return jsonify({'error': 'この教員には既に科目が設定されています'}), 409

    assignment = TeacherSubject(teacher_id=teacher.id, subject_id=subject_id)
    db.session.add(assignment)
    db.session.commit()
    return jsonify(assignment.to_dict()), 201


@teachers_bp.route('/<int:teacher_id>/subjects/<int:subject_id>', methods=['DELETE'])
@require_admin()
def remove_teacher_subject(teacher_id, subject_id):
    if not db.session.get(Teacher, teacher_id):
        return jsonify({'error': '該当する教員が見つかりません'}), 404
    assignment = TeacherSubject.query.filter_by(teacher_id=teacher_id, subject_id=subject_id).first()
    if not assignment:
        return jsonify({'error': '該当する担当可能科目が見つかりません'}), 404
    db.session.delete(assignment)
    db.session.commit()
    return jsonify({'message': '担当可能科目を削除しました'}), 200


@teachers_bp.route('/<int:teacher_id>/unavailable-slots', methods=['GET'])
@require_admin()
def get_teacher_unavailability(teacher_id):
    if not db.session.get(Teacher, teacher_id):
        return jsonify({'error': '該当する教員が見つかりません'}), 404
    slots = TeacherUnavailability.query.filter_by(teacher_id=teacher_id).order_by(
        TeacherUnavailability.day_of_week, TeacherUnavailability.period
    ).all()
    return jsonify([slot.to_dict() for slot in slots]), 200


@teachers_bp.route('/<int:teacher_id>/unavailable-slots', methods=['POST'])
@require_admin()
def add_teacher_unavailability(teacher_id):
    if not db.session.get(Teacher, teacher_id):
        return jsonify({'error': '該当する教員が見つかりません'}), 404
    data = request.get_json(silent=True) or {}
    day_of_week = data.get('day_of_week')
    period = data.get('period')
    if day_of_week not in VALID_DAYS:
        return jsonify({'error': 'day_of_week はMondayからFridayで指定してください'}), 400
    if period is not None and (isinstance(period, bool) or not isinstance(period, int) or not 1 <= period <= 5):
        return jsonify({'error': 'period はnullまたは1から5の整数で指定してください'}), 400
    if TeacherUnavailability.query.filter_by(
        teacher_id=teacher_id, day_of_week=day_of_week, period=period
    ).first():
        return jsonify({'error': '同じ出勤不可条件が既に登録されています'}), 409

    slot = TeacherUnavailability(teacher_id=teacher_id, day_of_week=day_of_week, period=period)
    db.session.add(slot)
    db.session.commit()
    return jsonify(slot.to_dict()), 201


@teachers_bp.route('/<int:teacher_id>/unavailable-slots/<int:slot_id>', methods=['DELETE'])
@require_admin()
def remove_teacher_unavailability(teacher_id, slot_id):
    if not db.session.get(Teacher, teacher_id):
        return jsonify({'error': '該当する教員が見つかりません'}), 404
    slot = TeacherUnavailability.query.filter_by(id=slot_id, teacher_id=teacher_id).first()
    if not slot:
        return jsonify({'error': '該当する出勤不可条件が見つかりません'}), 404
    db.session.delete(slot)
    db.session.commit()
    return jsonify({'message': '出勤不可条件を削除しました'}), 200


def _teacher_name_exists(name, exclude_id=None):
    #教員名の重複を確認するヘルパー関数
    query = Teacher.query.filter(db.func.lower(Teacher.name) == name.lower())
    if exclude_id is not None:
        query = query.filter(Teacher.id != exclude_id)
    return query.first() is not None
