from database import db

class Teacher(db.Model):
    __tablename__ = 'teachers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    employment_type = db.Column(db.String(20), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    subject = db.Column(db.String(100), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "employment_type": self.employment_type,
            "department": self.department,
            "subject": self.subject
        }