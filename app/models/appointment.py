from datetime import datetime
from app.models import db

class Appointment(db.Model):
    __tablename__ = 'appointments'
    
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id', ondelete='CASCADE'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id', ondelete='CASCADE'), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    time_slot = db.Column(db.String(50), nullable=False) # e.g. "09:00 - 09:30"
    status = db.Column(db.String(50), default='Pending') # 'Pending', 'Confirmed', 'Completed', 'Cancelled'
    reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Nurse Vitals Fields
    vitals_blood_pressure = db.Column(db.String(20), nullable=True) # e.g. "120/80"
    vitals_pulse = db.Column(db.Integer, nullable=True) # bpm
    vitals_temperature = db.Column(db.Float, nullable=True) # Fahrenheit
    vitals_height = db.Column(db.Float, nullable=True) # cm
    vitals_weight = db.Column(db.Float, nullable=True) # kg
    vitals_bmi = db.Column(db.Float, nullable=True)
    nurse_observations = db.Column(db.Text, nullable=True)
    vitals_recorded_at = db.Column(db.DateTime, nullable=True)

    # Unique constraint to prevent double-booking for a doctor
    __table_args__ = (
        db.UniqueConstraint('doctor_id', 'appointment_date', 'time_slot', name='unique_appointment_slot'),
    )

    # Relationships
    prescription = db.relationship('Prescription', backref='appointment', uselist=False, cascade="all, delete-orphan")
    bill = db.relationship('Bill', backref='appointment', uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Appointment {self.id}: Patient {self.patient_id} with Doctor {self.doctor_id} on {self.appointment_date} @ {self.time_slot}>"
