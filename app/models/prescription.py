from datetime import datetime
from app.models import db

class Prescription(db.Model):
    __tablename__ = 'prescriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id', ondelete='SET NULL'), unique=True, nullable=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id', ondelete='CASCADE'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False)
    symptoms = db.Column(db.Text, nullable=True)
    diagnosis = db.Column(db.Text, nullable=True)
    remarks = db.Column(db.Text, nullable=True)
    follow_up_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    medicines = db.relationship('PrescriptionMedicine', backref='prescription', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Prescription {self.id} for Patient {self.patient_id}>"


class PrescriptionMedicine(db.Model):
    __tablename__ = 'prescription_medicines'
    
    id = db.Column(db.Integer, primary_key=True)
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescriptions.id', ondelete='CASCADE'), nullable=False)
    medicine_name = db.Column(db.String(150), nullable=False)
    dosage_morning = db.Column(db.Boolean, default=False)
    dosage_afternoon = db.Column(db.Boolean, default=False)
    dosage_night = db.Column(db.Boolean, default=False)
    duration_days = db.Column(db.Integer, nullable=False, default=5)

    def __repr__(self):
        return f"<PrescriptionMedicine {self.medicine_name} for Prescription {self.prescription_id}>"
