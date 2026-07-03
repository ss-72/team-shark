from flask import Blueprint, jsonify, request

from database import db
from models.teacher import Teacher

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


def _teacher_name_exists(name, exclude_id=None):
    #教員名の重複を確認するヘルパー関数
    query = Teacher.query.filter(db.func.lower(Teacher.name) == name.lower())
    if exclude_id is not None:
        query = query.filter(Teacher.id != exclude_id)
    return query.first() is not None
