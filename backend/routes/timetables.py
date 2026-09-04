# backend/routes/timetables.py
from flask import Blueprint, jsonify, request
from database import db
from models.timetable import Timetable
from models.teacher import Teacher
from models.classroom import Classroom
from models.subject import KOMAS_PER_PERIOD, Subject
from models.teacher_subject import TeacherSubject
from models.teacher_unavailability import TeacherUnavailability, VALID_DAYS
from sqlalchemy.exc import IntegrityError
from services.timetable_generator import generate_timetable, TimetableGenerationError
from utils.auth import require_admin

# 時間割関連の API をまとめた Blueprint
timetables_bp = Blueprint('timetables_bp', __name__)


def _validated_manual_timetable(data, exclude_id=None):
    required_fields = ['day_of_week', 'period', 'teacher_id', 'subject_id', 'classroom_id']
    if not all(field in data for field in required_fields):
        return None, jsonify({'error': f'必須データが不足しています。必要: {required_fields}'}), 400

    day_of_week = data['day_of_week']
    period = data['period']
    teacher_id = data['teacher_id']
    subject_id = data['subject_id']
    classroom_id = data['classroom_id']
    if day_of_week not in VALID_DAYS:
        return None, jsonify({'error': 'day_of_week はMondayからFridayで指定してください'}), 400
    for field, value in [('period', period), ('teacher_id', teacher_id), ('subject_id', subject_id), ('classroom_id', classroom_id)]:
        if isinstance(value, bool) or not isinstance(value, int):
            return None, jsonify({'error': f'{field} は整数で指定してください'}), 400
    if not 1 <= period <= 5:
        return None, jsonify({'error': 'period は1から5で指定してください'}), 400
    if not db.session.get(Teacher, teacher_id) or not db.session.get(Classroom, classroom_id):
        return None, jsonify({'error': '指定された教員IDまたは教室IDが存在しません'}), 400
    subject = db.session.get(Subject, subject_id)
    if not subject:
        return None, jsonify({'error': '指定された科目IDが存在しません'}), 400
    if not TeacherSubject.query.filter_by(teacher_id=teacher_id, subject_id=subject_id).first():
        return None, jsonify({'error': '指定された教員はこの科目を担当できません'}), 400
    if TeacherUnavailability.query.filter_by(teacher_id=teacher_id, day_of_week=day_of_week, period=None).first() or \
            TeacherUnavailability.query.filter_by(teacher_id=teacher_id, day_of_week=day_of_week, period=period).first():
        return None, jsonify({'error': '指定された教員はその日時に出勤できません'}), 400

    teacher_conflict, classroom_conflict, grade_conflict = Timetable.find_conflicts(
        day_of_week, period, teacher_id=teacher_id, classroom_id=classroom_id,
        grade=subject.grade, exclude_id=exclude_id
    )
    if teacher_conflict:
        return None, jsonify({'error': '指定した教員はその日時に既に割当があります'}), 409
    if classroom_conflict:
        return None, jsonify({'error': '指定した教室はその日時に既に使用されています'}), 409
    if grade_conflict:
        return None, jsonify({'error': 'A class for this grade already exists at that time'}), 409
    return (day_of_week, period, teacher_id, subject_id, classroom_id), None, None


@timetables_bp.route('', methods=['GET'])
def get_timetables():
    #全ての時間割を取得して返すエンドポイント
    timetables = Timetable.query.all()
    return jsonify([t.to_dict() for t in timetables]), 200


@timetables_bp.route('', methods=['POST'])
@require_admin()
def create_timetable():
    #新しい時間割を登録するエンドポイント
    data = request.get_json(silent=True) or {}

    payload, response, status = _validated_manual_timetable(data)
    if response:
        return response, status
    day_of_week, period, teacher_id, subject_id, classroom_id = payload

    # 新しい時間割を作成して保存
    timetable = Timetable(
        day_of_week=day_of_week,
        period=period,
        teacher_id=teacher_id,
        subject_id=subject_id,
        classroom_id=classroom_id,
        is_online=data.get('is_online', False)
    )
    db.session.add(timetable)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "時間割の衝突が発生しました（整合性違反）"}), 409
    return jsonify(timetable.to_dict()), 201

@timetables_bp.route('/generate', methods=['POST'])
@require_admin()
def auto_generate():
    try:
        created = generate_timetable()
        return jsonify({
            "message": "時間割を自動生成しました",
            "count": len(created),
            "koma_count": len(created) * KOMAS_PER_PERIOD,
            "timetables": [t.to_dict() for t in created]
        }), 201
    except TimetableGenerationError as e:
        return jsonify({
            "error": "timetable_generation_failed",
            "shortages": e.shortages
        }), 422
    except ValueError as e:
        if e.args and isinstance(e.args[0], dict) and e.args[0].get('error') == 'timetable_generation_failed':
            return jsonify(e.args[0]), 422
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@timetables_bp.route('/<int:timetable_id>', methods=['GET'])
def get_timetable(timetable_id):
    #指定した時間割 ID を取得するエンドポイント
    timetable = Timetable.query.get(timetable_id)
    if not timetable:
        return jsonify({"error": "該当する時間割が見つかりません"}), 404
    return jsonify(timetable.to_dict()), 200


@timetables_bp.route('/<int:timetable_id>', methods=['PUT'])
@require_admin()
def update_timetable(timetable_id):
    #既存の時間割を更新するエンドポイント
    timetable = Timetable.query.get(timetable_id)
    if not timetable:
        return jsonify({"error": "該当する時間割が見つかりません"}), 404

    data = request.get_json(silent=True) or {}
    payload, response, status = _validated_manual_timetable(data, exclude_id=timetable.id)
    if response:
        return response, status
    day_of_week, period, teacher_id, subject_id, classroom_id = payload

    # レコードを更新して保存
    timetable.day_of_week = day_of_week
    timetable.period = period
    timetable.teacher_id = teacher_id
    timetable.subject_id = subject_id
    timetable.classroom_id = classroom_id
    timetable.is_online = data.get('is_online', False)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "時間割の衝突が発生しました（整合性違反）"}), 409
    return jsonify(timetable.to_dict()), 200


@timetables_bp.route('/<int:timetable_id>', methods=['DELETE'])
@require_admin()
def delete_timetable(timetable_id):
    #指定した時間割 ID を削除するエンドポイント
    timetable = Timetable.query.get(timetable_id)
    if not timetable:
        return jsonify({"error": "該当する時間割が見つかりません"}), 404
    
    db.session.delete(timetable)
    db.session.commit()
    return jsonify({"message": f"時間割ID {timetable_id} を削除しました"}), 200
