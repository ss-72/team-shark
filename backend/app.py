from datetime import time
import os
from urllib.parse import quote_plus

from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from database import db
from flask import session

from models.teacher import Teacher
from models.classroom import Classroom
from models.timetable import Timetable
from models.time_slot import TimeSlot
from models.user import User
from models.subject import Subject
from models.teacher_subject import TeacherSubject
from models.teacher_unavailability import TeacherUnavailability
from routes.classrooms import classrooms_bp
from routes.teachers import teachers_bp
from routes.time_slots import time_slots_bp
from routes.timetables import timetables_bp
from routes.auth import auth_bp
from routes.users import users_bp
from routes.subjects import subjects_bp
from routes.teacher_subjects import teacher_subjects_bp
from routes.teacher_unavailability import teacher_unavailability_bp

load_dotenv()


def _get_database_url():
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return database_url

    mysql_host = os.getenv('MYSQL_HOST')
    mysql_user = os.getenv('MYSQL_USER')
    mysql_password = os.getenv('MYSQL_PASSWORD')
    mysql_database = os.getenv('MYSQL_DATABASE')

    if mysql_host and mysql_user and mysql_password and mysql_database:
        mysql_port = os.getenv('MYSQL_PORT', '3306')
        return (
            f"mysql+pymysql://{quote_plus(mysql_user)}:{quote_plus(mysql_password)}"
            f"@{mysql_host}:{mysql_port}/{mysql_database}"
        )

    # 本番/運用向け: 明示的な DB 接続情報が必須
    raise RuntimeError('DATABASE_URL or MYSQL_HOST/MYSQL_USER/MYSQL_PASSWORD/MYSQL_DATABASE must be set')

def create_app(config_override=None):
    app = Flask(__name__)
    CORS(app)

    # Apply test overrides before consulting configuration that controls
    # startup validation.  This keeps the production fail-closed behavior
    # while allowing isolated test databases.
    if config_override:
        app.config.update(config_override)

    app.config['SQLALCHEMY_DATABASE_URI'] = app.config.get(
        'SQLALCHEMY_DATABASE_URI'
    ) or _get_database_url()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # セッションを使うためのシークレットキー
    # SECRET_KEY は本番で必須。テスト時はモック値を使えるようにする。
    secret = app.config.get('SECRET_KEY') or os.getenv('SECRET_KEY')
    if not secret and not app.config.get('TESTING'):
        raise RuntimeError('SECRET_KEY environment variable must be set')
    app.config['SECRET_KEY'] = secret or 'test-secret'
    db.init_app(app)

    # Register global auth/session checks
    from utils.auth import register_request_checks
    register_request_checks(app)

    app.register_blueprint(teachers_bp, url_prefix='/api/teachers')
    app.register_blueprint(classrooms_bp, url_prefix='/api/classrooms')
    app.register_blueprint(time_slots_bp, url_prefix='/api/time_slots')
    app.register_blueprint(timetables_bp, url_prefix='/api/timetables')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(subjects_bp, url_prefix='/api/subjects')
    app.register_blueprint(teacher_subjects_bp, url_prefix='/api/teacher_subjects')
    app.register_blueprint(teacher_unavailability_bp, url_prefix='/api/teacher_unavailability')

    with app.app_context():
        db.create_all()
        # Tests own their fixtures so development seed data cannot change their
        # assumptions or collide with records created by an individual test.
        if not app.config.get('TESTING'):
            _seed_time_slots()
            _seed_teachers()
            _seed_classrooms()
            _seed_admin_user()

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


def _seed_admin_user():
    # セキュリティ強化: 管理者の初期ユーザーは必ず環境変数で指定すること。
    # 非 TESTING モードで起動する場合、両方が未設定だと起動を中止して明示的に運用者に設定を促す。
    username = os.getenv('ADMIN_USERNAME')
    password = os.getenv('ADMIN_PASSWORD')

    if not username or not password:
        raise RuntimeError('Missing ADMIN_USERNAME or ADMIN_PASSWORD environment variables. Set both to seed initial admin.')

    # 既に存在すれば何もしない
    if User.query.filter_by(username=username).first():
        return

    admin = User(username=username, role='admin', is_active=True)
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
