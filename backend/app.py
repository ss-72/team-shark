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

    return app


def _seed_time_slots():
    if TimeSlot.query.count() > 0:
        return

    seed_rows = [
        TimeSlot(period=1, floor=None, start_time=time(9, 0), end_time=time(10, 30)),
        TimeSlot(period=2, floor=None, start_time=time(10, 45), end_time=time(12, 15)),
        TimeSlot(period=3, floor=None, start_time=time(12, 30), end_time=time(14, 0)),
        TimeSlot(period=4, floor=None, start_time=time(14, 15), end_time=time(15, 45)),
        TimeSlot(period=5, floor=None, start_time=time(16, 0), end_time=time(17, 30)),
        TimeSlot(period=3, floor=3, start_time=time(12, 45), end_time=time(14, 15)),
    ]
    db.session.add_all(seed_rows)
    db.session.commit()

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)