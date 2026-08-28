from sqlalchemy import UniqueConstraint

from database import db


class TeacherSubject(db.Model):
    __tablename__ = 'teacher_subjects'
    __table_args__ = (
        UniqueConstraint('teacher_id', 'subject_id', name='u_teacher_subject'),
    )

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)

    teacher = db.relationship('Teacher', backref='subject_assignments')
    subject = db.relationship('Subject', backref='teacher_assignments')

    def to_dict(self):
        return {
            'teacher_id': self.teacher_id,
            'subject_id': self.subject_id,
            'subject': self.subject.to_dict() if self.subject else None,
        }
