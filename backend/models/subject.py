from sqlalchemy import CheckConstraint

from database import db

KOMAS_PER_PERIOD = 2


class Subject(db.Model):
    __tablename__ = 'subjects'
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name='ck_subject_name_not_blank'),
        CheckConstraint('required_periods_per_week >= 2', name='ck_subject_required_periods_minimum'),
        CheckConstraint('required_periods_per_week % 2 = 0', name='ck_subject_required_periods_even'),
        CheckConstraint('grade IN (2, 3, 4)', name='ck_subject_grade_supported'),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    required_periods_per_week = db.Column(db.Integer, nullable=False)
    grade = db.Column(db.Integer, nullable=False, server_default='2')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'required_periods_per_week': self.required_periods_per_week,
            'grade': self.grade,
        }
