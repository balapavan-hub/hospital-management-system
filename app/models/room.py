from datetime import datetime
from app.models import db

class Room(db.Model):
    __tablename__ = 'rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id', ondelete='CASCADE'), nullable=False)
    room_number = db.Column(db.String(20), nullable=False)
    room_type = db.Column(db.String(50), nullable=False) # e.g. General Ward, Semi-Private, Private Room, ICU, Operation Theater
    status = db.Column(db.String(50), default='Available') # Available, Occupied, Under Maintenance
    rate_per_day = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Unique constraint per hospital
    __table_args__ = (
        db.UniqueConstraint('hospital_id', 'room_number', name='unique_hospital_room'),
    )

    def __repr__(self):
        return f"<Room {self.room_number} ({self.room_type})>"
