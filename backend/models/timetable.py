from database import db

class Timetable(db.Model):
    __tablename__ = 'timetables'
    
    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.String(10), nullable=False) # 'Monday', 'Tuesday' など
    period = db.Column(db.Integer, nullable=False)          # 1限, 2限 など
    
    # 外部キーの設定
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)

    # モデル間のリレーションシップ（JOIN して情報を取得しやすくするための設定）
    teacher = db.relationship('Teacher', backref='timetables')
    classroom = db.relationship('Classroom', backref='timetables')

    def to_dict(self):
        return {
            "id": self.id,
            "day_of_week": self.day_of_week,
            "period": self.period,
            "teacher_id": self.teacher_id,
            "classroom_id": self.classroom_id,
            "teacher_name": self.teacher.name if self.teacher else None,
            "classroom_name": self.classroom.name if self.classroom else None
        }