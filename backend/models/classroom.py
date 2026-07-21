from database import db

class Classroom(db.Model):
    __tablename__ = 'classrooms'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    capacity = db.Column(db.Integer, nullable=True)
    floor = db.Column(db.Integer, nullable=True)
    priority_department = db.Column(db.String(100), nullable=True)
    supports_online = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "capacity": self.capacity,
            "floor": self.floor,
            "priority_department": self.priority_department,
            "supports_online": self.supports_online,
        }