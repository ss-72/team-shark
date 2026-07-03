from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from database import db
from models.classroom import Classroom

# 教室関連の API をまとめた Blueprint
classrooms_bp = Blueprint('classrooms_bp', __name__)


@classrooms_bp.route('', methods=['GET'])
def get_classrooms():
    # 全ての教室を取得して JSON として返す
    classrooms = Classroom.query.all()
    return jsonify([classroom.to_dict() for classroom in classrooms]), 200


@classrooms_bp.route('', methods=['POST'])
def create_classroom():
    # POST リクエストから JSON データを取得
    data = request.get_json(silent=True) or {}

    # 教室名は必須フィールドとして検証
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({"error": "教室名 (name) は必須です"}), 400

    # 重複する教室名が存在するか確認
    if _classroom_name_exists(name):
        return jsonify({"error": f"教室名「{name}」は既に登録されています"}), 409

    # Classroom オブジェクトを生成し、DB へ追加
    classroom = Classroom(
        name=name,
        capacity=data.get('capacity'),
        floor=data.get('floor'),
        priority_department=data.get('priority_department'),
    )
    db.session.add(classroom)
    try:
        db.session.commit()
    except IntegrityError:
        # 一意制約違反などの整合性エラー時はロールバックしてエラーを返す
        db.session.rollback()
        return jsonify({"error": f"教室名「{name}」は既に登録されています"}), 409
    return jsonify({**classroom.to_dict(), "message": "教室を登録しました"}), 201


@classrooms_bp.route('/<int:classroom_id>', methods=['GET'])
def get_classroom(classroom_id):
    # 指定 ID の教室を取得し、存在しなければ 404 を返す
    classroom = Classroom.query.get(classroom_id)
    if not classroom:
        return jsonify({"error": "該当する教室が見つかりません"}), 404
    return jsonify(classroom.to_dict()), 200


@classrooms_bp.route('/<int:classroom_id>', methods=['PUT'])
def update_classroom(classroom_id):
    # 既存の教室を更新する処理
    classroom = Classroom.query.get(classroom_id)
    if not classroom:
        return jsonify({"error": "該当する教室が見つかりません"}), 404

    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({"error": "教室名 (name) は必須です"}), 400

    # 他の教室と名前が重複しないように確認（自身は除外）
    if _classroom_name_exists(name, exclude_id=classroom_id):
        return jsonify({"error": f"教室名「{name}」は既に登録されています"}), 409

    classroom.name = name
    classroom.capacity = data.get('capacity')
    classroom.floor = data.get('floor')
    classroom.priority_department = data.get('priority_department')

    try:
        db.session.commit()
    except IntegrityError:
        # 更新時に整合性違反が起きた場合はロールバックしてエラーを返す
        db.session.rollback()
        return jsonify({"error": f"教室名「{name}」は既に登録されています"}), 409
    return jsonify({**classroom.to_dict(), "message": "教室情報を更新しました"}), 200


@classrooms_bp.route('/<int:classroom_id>', methods=['DELETE'])
def delete_classroom(classroom_id):
    # 指定 ID の教室を削除する処理
    classroom = Classroom.query.get(classroom_id)
    if not classroom:
        return jsonify({"error": "該当する教室が見つかりません"}), 404

    db.session.delete(classroom)
    db.session.commit()
    return jsonify({"message": f"教室ID {classroom_id} を削除しました"}), 200


def _classroom_name_exists(name, exclude_id=None):
    # 指定名の教室が既に存在するかをチェックするヘルパー関数
    query = Classroom.query.filter(db.func.lower(Classroom.name) == name.lower())
    if exclude_id is not None:
        query = query.filter(Classroom.id != exclude_id)
    return query.first() is not None
