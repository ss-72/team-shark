from flask import Blueprint, jsonify, session
from database import db
from models.timetable import Timetable
from models.user import User
from utils.auth import current_user

my_timetable_bp = Blueprint('my_timetable_bp', __name__)

DAY_ORDER = {
    'Monday': 1,
    'Tuesday': 2,
    'Wednesday': 3,
    'Thursday': 4,
    'Friday': 5,
}


@my_timetable_bp.route('', methods=['GET'])
@my_timetable_bp.route('/', methods=['GET'])
def get_my_timetable():
    """教員本人の時間割を取得するエンドポイント"""
    user = current_user()
    if not user or not user.is_active:
        return jsonify({'error': 'unauthenticated'}), 401

    if user.role != 'teacher':
        return jsonify({'error': 'forbidden'}), 403

    if not user.teacher_id:
        return jsonify({'error': 'teacher_profile_not_linked'}), 400

    # サーバー側の user.teacher_id のみを信頼し、クエリパラメータは使用しない
    timetables = Timetable.query.filter_by(teacher_id=user.teacher_id).all()

    # 曜日・時限順にソート
    timetables.sort(key=lambda t: (DAY_ORDER.get(t.day_of_week, 99), t.period))

    result = []
    for t in timetables:
        subj_name = t.subject.name if t.subject else None
        room_name = t.classroom.name if t.classroom else None
        result.append({
            'id': t.id,
            'teacher_id': t.teacher_id,
            'day_of_week': t.day_of_week,
            'period': t.period,
            'subject_id': t.subject_id,
            'subject': subj_name,
            'subject_name': subj_name,
            'grade': t.subject.grade if t.subject else None,
            'classroom_id': t.classroom_id,
            'classroom': room_name,
            'classroom_name': room_name,
            'is_online': t.is_online,
        })

    return jsonify(result), 200
