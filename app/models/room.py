from datetime import datetime
from app.models import db

class Room(db.Model):
    __tablename__ = 'rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(20), unique=True, nullable=False)
    room_type = db.Column(db.String(50), nullable=False) # e.g. General, ICU, Private
    status = db.Column(db.String(50), default='Available') # Available, Occupied, Under Maintenance
    rate_per_day = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Room {self.room_number} ({self.room_type})>"
