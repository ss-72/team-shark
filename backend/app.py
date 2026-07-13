from datetime import time

from flask import Flask
from flask_cors import CORS
from database import db

from models.teacher import Teacher
from models.classroom import Classroom
from models.timetable import Timetable
from models.time_slot import TimeSlot
from routes.classrooms import classrooms_bp
from routes.teachers import teachers_bp
from routes.time_slots import time_slots_bp
from routes.timetables import timetables_bp

def create_app(config_override=None):
    app = Flask(__name__)
    CORS(app)

    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://scrum_user:password123@localhost/school_db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    if config_override:
        app.config.update(config_override)

    db.init_app(app)

    app.register_blueprint(teachers_bp, url_prefix='/api/teachers')
    app.register_blueprint(classrooms_bp, url_prefix='/api/classrooms')
    app.register_blueprint(time_slots_bp, url_prefix='/api/time_slots')
    app.register_blueprint(timetables_bp, url_prefix='/api/timetables')

    with app.app_context():
        db.create_all()
        _seed_time_slots()
        _seed_teachers()
        _seed_classrooms()

    return app


def _seed_teachers():
    if Teacher.query.count() > 0:
        return

    seed_rows = [
        Teacher(name='山田 太郎', employment_type='常勤', department='情報科学科', subject='数学'),
        Teacher(name='田中 花子', employment_type='常勤', department='国語科', subject='国語'),
        Teacher(name='佐藤 次郎', employment_type='常勤', department='英語科', subject='英語'),
        Teacher(name='鈴木 一郎', employment_type='非常勤', department='体育科', subject='体育'),
        Teacher(name='高橋 美咲', employment_type='非常勤', department='美術科', subject='美術'),
    ]
    db.session.add_all(seed_rows)
    db.session.commit()


def _seed_classrooms():
    if Classroom.query.count() > 0:
        return

    seed_rows = [
        Classroom(name='101教室', capacity=40, floor=1, priority_department='情報科学科'),
        Classroom(name='201教室', capacity=35, floor=2, priority_department='国語科'),
        Classroom(name='理科室', capacity=30, floor=3, priority_department='理科'),
        Classroom(name='体育館', capacity=200, floor=1, priority_department='体育科'),
    ]
    db.session.add_all(seed_rows)
    db.session.commit()


def _seed_time_slots():
    if TimeSlot.query.count() > 0:
        return

    seed_rows = [
        TimeSlot(period=1, floor=None, start_time=time(9, 0), end_time=time(10, 30)),
        TimeSlot(period=2, floor=None, start_time=time(10, 45), end_time=time(12, 15)),
        TimeSlot(period=3, floor=None, start_time=time(13, 0), end_time=time(14, 30)),
        TimeSlot(period=4, floor=None, start_time=time(14, 45), end_time=time(16, 15)),
        TimeSlot(period=5, floor=None, start_time=time(16, 30), end_time=time(18, 0)),
    ]
    db.session.add_all(seed_rows)
    db.session.commit()

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)