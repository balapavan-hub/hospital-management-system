from datetime import datetime
from app.models import db

class Appointment(db.Model):
    __tablename__ = 'appointments'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id', ondelete='CASCADE'), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    time_slot = db.Column(db.String(50), nullable=False) # e.g. "09:00 - 09:30"
    status = db.Column(db.Enum('Pending', 'Confirmed', 'Completed', 'Cancelled', name='appointment_status'), default='Pending')
    reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Unique constraint to prevent double-booking for a doctor
    __table_args__ = (
        db.UniqueConstraint('doctor_id', 'appointment_date', 'time_slot', name='unique_appointment_slot'),
    )

    # Relationships
    prescription = db.relationship('Prescription', backref='appointment', uselist=False, cascade="all, delete-orphan")
    bill = db.relationship('Bill', backref='appointment', uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Appointment {self.id}: Patient {self.patient_id} with Doctor {self.doctor_id} on {self.appointment_date} @ {self.time_slot}>"
