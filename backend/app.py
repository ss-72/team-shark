from datetime import time
import os
from urllib.parse import quote_plus

from flask import Flask, send_from_directory
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
from routes.my_timetable import my_timetable_bp

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
    app = Flask(__name__, static_folder='../frontend', static_url_path='')
    CORS(
        app,
        supports_credentials=True,
        origins=['http://localhost:8080', 'http://127.0.0.1:8080'],
    )

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
    app.register_blueprint(my_timetable_bp, url_prefix='/api/my/timetable')

    @app.route('/')
    def frontend_index():
        return send_from_directory(app.static_folder, 'index.html')

    with app.app_context():
        db.create_all()
        # Tests own their fixtures so development seed data cannot change their
        # assumptions or collide with records created by an individual test.
        if not app.config.get('TESTING'):
            _seed_time_slots()
            _seed_teachers()
            _seed_classrooms()
            _seed_admin_user()
            _seed_demo_data()

    return app


def _seed_teachers():
    teachers_data = [
        {'name': '山田 太郎', 'employment_type': '常勤', 'department': '高度ITエンジニア科', 'subject': ''},
        {'name': '田中 花子', 'employment_type': '常勤', 'department': '高度ITエンジニア科', 'subject': ''},
        {'name': '佐藤 次郎', 'employment_type': '常勤', 'department': '高度ITエンジニア科', 'subject': ''},
        {'name': '鈴木 一郎', 'employment_type': '非常勤', 'department': '高度ITエンジニア科', 'subject': ''},
        {'name': '高橋 美咲', 'employment_type': '非常勤', 'department': '高度ITエンジニア科', 'subject': ''},
    ]
    for data in teachers_data:
        teacher = Teacher.query.filter_by(name=data['name']).first()
        if not teacher:
            db.session.add(Teacher(**data))
        else:
            teacher.employment_type = data['employment_type']
            teacher.department = data['department']
            teacher.subject = data['subject']
    db.session.commit()


def _seed_classrooms():
    classrooms_data = [
        {'name': 'PC実習室A', 'capacity': 40, 'floor': 5, 'priority_department': '高度ITエンジニア科'},
        {'name': 'PC実習室B', 'capacity': 40, 'floor': 5, 'priority_department': '高度ITエンジニア科'},
        {'name': 'システム実習室', 'capacity': 30, 'floor': 6, 'priority_department': '高度ITエンジニア科'},
        {'name': '講義室A', 'capacity': 50, 'floor': 6, 'priority_department': '高度ITエンジニア科'},
    ]
    for data in classrooms_data:
        classroom = Classroom.query.filter_by(name=data['name']).first()
        if not classroom:
            db.session.add(Classroom(**data))
        else:
            classroom.capacity = data['capacity']
            classroom.floor = data['floor']
            classroom.priority_department = data['priority_department']
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


def _seed_demo_data():
    # 高度ITエンジニア科 2025年度カリキュラムに基づく科目データ
    subjects_data = [
        {'name': 'チーム開発技法', 'required_periods_per_week': 6},
        {'name': 'WEBアプリケーション', 'required_periods_per_week': 4},
        {'name': 'プログラミング言語Ⅲ', 'required_periods_per_week': 4},
        {'name': 'クラウド技術基礎', 'required_periods_per_week': 3},
        {'name': '情報セキュリティⅡ', 'required_periods_per_week': 3},
        {'name': 'データベース設計', 'required_periods_per_week': 2},
        {'name': 'サーバ構築', 'required_periods_per_week': 2},
        {'name': 'システム開発演習', 'required_periods_per_week': 2},
    ]
    subject_map = {}
    for s_data in subjects_data:
        subj = Subject.query.filter_by(name=s_data['name']).first()
        if not subj:
            subj = Subject(**s_data)
            db.session.add(subj)
            db.session.flush()
        else:
            subj.required_periods_per_week = s_data['required_periods_per_week']
        subject_map[s_data['name']] = subj
    db.session.commit()

    # 教員ごとの担当可能科目 (TeacherSubject)
    teacher_assignments = {
        '山田 太郎': ['チーム開発技法', 'WEBアプリケーション', 'システム開発演習'],
        '田中 花子': ['プログラミング言語Ⅲ', 'データベース設計'],
        '佐藤 次郎': ['サーバ構築', 'クラウド技術基礎'],
        '鈴木 一郎': ['情報セキュリティⅡ', 'WEBアプリケーション'],
        '高橋 美咲': ['チーム開発技法', 'システム開発演習'],
    }
    for teacher_name, sub_names in teacher_assignments.items():
        teacher = Teacher.query.filter_by(name=teacher_name).first()
        if not teacher:
            continue
        for sub_name in sub_names:
            subj = subject_map.get(sub_name) or Subject.query.filter_by(name=sub_name).first()
            if not subj:
                continue
            exists = TeacherSubject.query.filter_by(teacher_id=teacher.id, subject_id=subj.id).first()
            if not exists:
                db.session.add(TeacherSubject(teacher_id=teacher.id, subject_id=subj.id))
    db.session.commit()

    # 出勤不可条件 (TeacherUnavailability)
    # 山田 太郎: 火曜日 終日不可, 木曜日 3限不可
    # 佐藤 次郎: 水曜日 1限不可
    unavailabilities = [
        ('山田 太郎', 'Tuesday', None),
        ('山田 太郎', 'Thursday', 3),
        ('佐藤 次郎', 'Wednesday', 1),
    ]
    for teacher_name, day, period in unavailabilities:
        teacher = Teacher.query.filter_by(name=teacher_name).first()
        if not teacher:
            continue
        exists = TeacherUnavailability.query.filter_by(teacher_id=teacher.id, day_of_week=day, period=period).first()
        if not exists:
            db.session.add(TeacherUnavailability(teacher_id=teacher.id, day_of_week=day, period=period))
    db.session.commit()

    # デモ用の教員ログインアカウント（山田 太郎先生に紐付け）
    yamada = Teacher.query.filter_by(name='山田 太郎').first()
    teacher_user = User.query.filter_by(username='teacher').first()
    if not teacher_user:
        teacher_user = User(
            username='teacher',
            role='teacher',
            teacher_id=yamada.id if yamada else None,
            is_active=True
        )
        teacher_user.set_password('teacher123')
        db.session.add(teacher_user)
    else:
        if yamada and teacher_user.teacher_id != yamada.id:
            teacher_user.teacher_id = yamada.id
    db.session.commit()


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
