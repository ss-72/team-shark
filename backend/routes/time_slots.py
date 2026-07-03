from datetime import datetime
from flask import Blueprint, jsonify, request

from database import db
from models.time_slot import TimeSlot

# 時間枠関連の API をまとめた Blueprint
time_slots_bp = Blueprint('time_slots_bp', __name__)


@time_slots_bp.route('', methods=['GET'])
def get_time_slots():
    """全ての時間枠を取得して返すエンドポイント"""

    # period と floor の昇順で並べ替えて返す
    time_slots = TimeSlot.query.order_by(TimeSlot.period.asc(), TimeSlot.floor.asc()).all()
    return jsonify([time_slot.to_dict() for time_slot in time_slots]), 200


@time_slots_bp.route('', methods=['POST'])
def create_time_slot():
    """新しい時間枠を作成するエンドポイント"""
    data = request.get_json(silent=True) or {}

    # 必須フィールドがすべて提供されているか確認する
    required_fields = ['period', 'start_time', 'end_time']
    if not all(field in data for field in required_fields):
        return jsonify({"error": f"必須データが不足しています。必要: {required_fields}"}), 400

    # 時刻文字列を解析し、時間オブジェクトに変換する
    start_time = _parse_time(data['start_time'])
    end_time = _parse_time(data['end_time'])
    if start_time is None or end_time is None:
        return jsonify({"error": "start_time / end_time は HH:MM 形式で指定してください"}), 400
    if start_time >= end_time:
        return jsonify({"error": "start_time は end_time より前である必要があります"}), 400

    # period は必須、floor は任意で数値に変換
    period = int(data['period'])
    floor = int(data['floor']) if data.get('floor') is not None else None

    # 同じ period/floor の重複登録を防ぐ
    if _period_exists(period, floor):
        return jsonify({"error": f"{period}時限（floor={floor}）は既に登録されています"}), 409

    # start_time/end_time が既存の時間枠と重複しないか確認
    conflict = _find_time_overlap(floor, start_time, end_time)
    if conflict:
        return jsonify({"error": f"指定した時間帯は既存の時間枠（ID {conflict.id}）と重複しています"}), 409

    # 新しい TimeSlot を作成して保存
    time_slot = TimeSlot(
        period=period,
        floor=floor,
        start_time=start_time,
        end_time=end_time,
    )
    db.session.add(time_slot)
    db.session.commit()
    return jsonify({**time_slot.to_dict(), "message": "時間枠を登録しました"}), 201


@time_slots_bp.route('/<int:time_slot_id>', methods=['GET'])
def get_time_slot(time_slot_id):
    """指定 ID の時間枠を取得するエンドポイント"""
    time_slot = TimeSlot.query.get(time_slot_id)
    if not time_slot:
        return jsonify({"error": "該当する時間枠が見つかりません"}), 404
    return jsonify(time_slot.to_dict()), 200


@time_slots_bp.route('/<int:time_slot_id>', methods=['PUT'])
def update_time_slot(time_slot_id):
    """既存の時間枠を更新するエンドポイント"""
    time_slot = TimeSlot.query.get(time_slot_id)
    if not time_slot:
        return jsonify({"error": "該当する時間枠が見つかりません"}), 404

    data = request.get_json(silent=True) or {}
    required_fields = ['period', 'start_time', 'end_time']
    if not all(field in data for field in required_fields):
        return jsonify({"error": f"必須データが不足しています。必要: {required_fields}"}), 400

    start_time = _parse_time(data['start_time'])
    end_time = _parse_time(data['end_time'])
    if start_time is None or end_time is None:
        return jsonify({"error": "start_time / end_time は HH:MM 形式で指定してください"}), 400
    if start_time >= end_time:
        return jsonify({"error": "start_time は end_time より前である必要があります"}), 400

    period = int(data['period'])
    floor = int(data['floor']) if data.get('floor') is not None else None

    # 更新時は自分自身を除外して重複チェックを行う
    if _period_exists(period, floor, exclude_id=time_slot_id):
        return jsonify({"error": f"{period}時限（floor={floor}）は既に登録されています"}), 409

    # 更新後の時間帯が他の時間枠と重複しないか確認
    conflict = _find_time_overlap(floor, start_time, end_time, exclude_id=time_slot_id)
    if conflict:
        return jsonify({"error": f"指定した時間帯は既存の時間枠（ID {conflict.id}）と重複しています"}), 409

    # DB 上のレコードを更新して保存
    time_slot.period = period
    time_slot.floor = floor
    time_slot.start_time = start_time
    time_slot.end_time = end_time

    db.session.commit()
    return jsonify({**time_slot.to_dict(), "message": "時間枠を更新しました"}), 200

@time_slots_bp.route('/<int:time_slot_id>', methods=['DELETE'])
def delete_time_slot(time_slot_id):
#指定 ID の時間枠を削除するエンドポイント
    time_slot = TimeSlot.query.get(time_slot_id)
    if not time_slot:
        return jsonify({"error": "該当する時間枠が見つかりません"}), 404

    db.session.delete(time_slot)
    db.session.commit()
    return jsonify({"message": f"時間枠ID {time_slot_id} を削除しました"}), 200


def _parse_time(value):
#受け取った値を time オブジェクトへ変換する。HH:MM 形式の文字列を想定。
    if hasattr(value, 'hour') and hasattr(value, 'minute'):
        return value

    try:
        return datetime.strptime(value, '%H:%M').time()
    except (TypeError, ValueError):
        return None


def _period_exists(period, floor, exclude_id=None):
#同じ floor 内で同じ period の時間枠が存在するかどうか確認する。
    query = TimeSlot.query.filter(TimeSlot.period == period, TimeSlot.floor == floor)
    if exclude_id is not None:
        query = query.filter(TimeSlot.id != exclude_id)
    return query.first() is not None


def _find_time_overlap(floor, start_time, end_time, exclude_id=None):
#指定時間帯が同じ floor 上の他の時間枠と重複するか確認する。
    query = TimeSlot.query.filter(
        TimeSlot.floor == floor,
        TimeSlot.start_time < end_time,
        TimeSlot.end_time > start_time,
    )
    if exclude_id is not None:
        query = query.filter(TimeSlot.id != exclude_id)
    return query.first()
