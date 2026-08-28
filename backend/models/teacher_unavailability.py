from sqlalchemy import CheckConstraint, UniqueConstraint

from database import db


VALID_DAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday')


class TeacherUnavailability(db.Model):
    __tablename__ = 'teacher_unavailability'
    __table_args__ = (
        CheckConstraint(
            "day_of_week IN ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday')",
            name='ck_teacher_unavailability_day',
        ),
        CheckConstraint('period IS NULL OR period BETWEEN 1 AND 5', name='ck_teacher_unavailability_period'),
        UniqueConstraint('teacher_id', 'day_of_week', 'period', name='u_teacher_unavailability'),
    )

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    day_of_week = db.Column(db.String(10), nullable=False)
    period = db.Column(db.Integer, nullable=True)

    teacher = db.relationship('Teacher', backref='unavailable_slots')

    def to_dict(self):
        return {
            'id': self.id,
            'teacher_id': self.teacher_id,
            'day_of_week': self.day_of_week,
            'period': self.period,
        }
