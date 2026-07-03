from database import db


class TimeSlot(db.Model):
    __tablename__ = 'time_slots'

    id = db.Column(db.Integer, primary_key=True)
    period = db.Column(db.Integer, nullable=False)
    floor = db.Column(db.Integer, nullable=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "period": self.period,
            "floor": self.floor,
            "start_time": self.start_time.strftime("%H:%M") if self.start_time else None,
            "end_time": self.end_time.strftime("%H:%M") if self.end_time else None,
        }