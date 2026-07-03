# backend/routes/timetables.py
from flask import Blueprint, jsonify, request
from database import db
from models.timetable import Timetable
from models.teacher import Teacher
from models.classroom import Classroom
from sqlalchemy.exc import IntegrityError
from services.timetable_generator import generate_timetable

# 時間割関連の API をまとめた Blueprint
timetables_bp = Blueprint('timetables_bp', __name__)


@timetables_bp.route('', methods=['GET'])
def get_timetables():
    #全ての時間割を取得して返すエンドポイント
    timetables = Timetable.query.all()
    return jsonify([t.to_dict() for t in timetables]), 200


@timetables_bp.route('', methods=['POST'])
def create_timetable():
    #新しい時間割を登録するエンドポイント
    data = request.get_json(silent=True) or {}

    # 必須フィールドの存在確認
    required_fields = ['day_of_week', 'period', 'teacher_id', 'classroom_id']
    if not all(field in data for field in required_fields):
        return jsonify({"error": f"必須データが不足しています。必要: {required_fields}"}), 400
    
    # 指定された教員と教室が DB に存在することを確認
    teacher_exists = Teacher.query.get(data['teacher_id'])
    classroom_exists = Classroom.query.get(data['classroom_id'])
    if not teacher_exists or not classroom_exists:
        return jsonify({"error": "指定された教員IDまたは教室IDが存在しません"}), 400

    # 重複チェック: モデルの共通メソッドで確認（DB整合性と二重チェック）
    period = int(data['period'])
    teacher_id = int(data['teacher_id'])
    classroom_id = int(data['classroom_id'])

    t_conflict, c_conflict = Timetable.find_conflicts(
        data['day_of_week'], period, teacher_id=teacher_id, classroom_id=classroom_id
    )
    if t_conflict:
        return jsonify({"error": "指定した教員はその日時に既に割当があります"}), 409
    if c_conflict:
        return jsonify({"error": "指定した教室はその日時に既に使用されています"}), 409

    # 新しい時間割を作成して保存
    timetable = Timetable(
        day_of_week=data['day_of_week'],
        period=period,
        teacher_id=teacher_id,
        classroom_id=classroom_id
    )
    db.session.add(timetable)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "時間割の衝突が発生しました（整合性違反）"}), 409
    return jsonify(timetable.to_dict()), 201

@timetables_bp.route('/generate', methods=['POST'])
def auto_generate():
    try:
        created = generate_timetable()
        return jsonify({
            "message": f"時間割を自動生成しました",
            "count": len(created),
            "timetables": [t.to_dict() for t in created]
        }), 201
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
def update_timetable(timetable_id):
    #既存の時間割を更新するエンドポイント
    timetable = Timetable.query.get(timetable_id)
    if not timetable:
        return jsonify({"error": "該当する時間割が見つかりません"}), 404

    data = request.get_json(silent=True) or {}
    required_fields = ['day_of_week', 'period', 'teacher_id', 'classroom_id']
    if not all(field in data for field in required_fields):
        return jsonify({"error": f"必須データが不足しています。必要: {required_fields}"}), 400

    teacher_exists = Teacher.query.get(data['teacher_id'])
    classroom_exists = Classroom.query.get(data['classroom_id'])
    if not teacher_exists or not classroom_exists:
        return jsonify({"error": "指定された教員IDまたは教室IDが存在しません"}), 400

    # 更新時の重複チェック: 自身のレコードは除外して確認する
    period = int(data['period'])
    teacher_id = int(data['teacher_id'])
    classroom_id = int(data['classroom_id'])

    t_conflict, c_conflict = Timetable.find_conflicts(
        data['day_of_week'], period, teacher_id=teacher_id, classroom_id=classroom_id, exclude_id=timetable.id
    )
    if t_conflict:
        return jsonify({"error": "指定した教員はその日時に既に割当があります"}), 409
    if c_conflict:
        return jsonify({"error": "指定した教室はその日時に既に使用されています"}), 409

    # レコードを更新して保存
    timetable.day_of_week = data['day_of_week']
    timetable.period = period
    timetable.teacher_id = teacher_id
    timetable.classroom_id = classroom_id

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "時間割の衝突が発生しました（整合性違反）"}), 409
    return jsonify(timetable.to_dict()), 200


@timetables_bp.route('/<int:timetable_id>', methods=['DELETE'])
def delete_timetable(timetable_id):
#指定した時間割 ID を削除するエンドポイント
    timetable = Timetable.query.get(timetable_id)
    if not timetable:
        return jsonify({"error": "該当する時間割が見つかりません"}), 404
    
    db.session.delete(timetable)
    db.session.commit()
    return jsonify({"message": f"時間割ID {timetable_id} を削除しました"}), 200