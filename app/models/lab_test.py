from datetime import datetime
from app.models import db

class LabTest(db.Model):
    __tablename__ = 'lab_tests'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id', ondelete='SET NULL'), nullable=True)
    test_name = db.Column(db.String(150), nullable=False)
    test_category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='Ordered')  # Ordered, Sample Collected, In Progress, Completed, Cancelled
    result_value = db.Column(db.Text, nullable=True)
    normal_range = db.Column(db.String(200), nullable=True)
    unit = db.Column(db.String(50), nullable=True)
    result_status = db.Column(db.String(50), nullable=True)  # Normal, Abnormal, Critical
    remarks = db.Column(db.Text, nullable=True)
    report_file = db.Column(db.String(255), nullable=True)
    test_date = db.Column(db.DateTime, default=datetime.utcnow)
    result_date = db.Column(db.DateTime, nullable=True)
    cost = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    
    def __repr__(self):
        return f"<LabTest {self.test_name} for Patient {self.patient_id}>"
