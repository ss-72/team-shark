from database import db
from models.subject import Subject
from sqlalchemy import UniqueConstraint

class Timetable(db.Model):
    __tablename__ = 'timetables'
    __table_args__ = (
        UniqueConstraint('day_of_week', 'period', 'teacher_id', name='u_teacher_slot'),
        UniqueConstraint('day_of_week', 'period', 'classroom_id', name='u_classroom_slot'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.String(10), nullable=False) # 'Monday', 'Tuesday' など
    period = db.Column(db.Integer, nullable=False)          # 1限, 2限 など
    is_online = db.Column(db.Boolean, default=False) 
    
    # 外部キーの設定
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)

    # モデル間のリレーションシップ（JOIN して情報を取得しやすくするための設定）
    teacher = db.relationship('Teacher', backref='timetables')
    subject = db.relationship('Subject', backref='timetables')
    classroom = db.relationship('Classroom', backref='timetables')

    def to_dict(self):
        return {
            "id": self.id,
            "day_of_week": self.day_of_week,
            "period": self.period,
            "teacher_id": self.teacher_id,
            "subject_id": self.subject_id,
            "classroom_id": self.classroom_id,
            "is_online": self.is_online,
            "teacher_name": self.teacher.name if self.teacher else None,
            "subject_name": self.subject.name if self.subject else None,
            "grade": self.subject.grade if self.subject else None,
            "classroom_name": self.classroom.name if self.classroom else None
        }

    @classmethod
    def find_conflicts(cls, day_of_week, period, teacher_id=None, classroom_id=None, grade=None, exclude_id=None):
        """
        指定したスロットで教員または教室の衝突があるか確認する。
        exclude_id を指定するとそのレコードは検索から除外する（更新時に自身を無視するため）。
        戻り値: (teacher_conflict, classroom_conflict) — 存在しない場合は None。
        """
        teacher_conflict = None
        classroom_conflict = None

        if teacher_id is not None:
            q = cls.query.filter_by(day_of_week=day_of_week, period=period, teacher_id=teacher_id)
            if exclude_id is not None:
                q = q.filter(cls.id != exclude_id)
            teacher_conflict = q.first()

        if classroom_id is not None:
            q = cls.query.filter_by(day_of_week=day_of_week, period=period, classroom_id=classroom_id)
            if exclude_id is not None:
                q = q.filter(cls.id != exclude_id)
            classroom_conflict = q.first()

        grade_conflict = None
        if grade is not None:
            q = cls.query.join(Subject, cls.subject_id == Subject.id).filter(
                cls.day_of_week == day_of_week,
                cls.period == period,
                Subject.grade == grade,
            )
            if exclude_id is not None:
                q = q.filter(cls.id != exclude_id)
            grade_conflict = q.first()

        return teacher_conflict, classroom_conflict, grade_conflict
