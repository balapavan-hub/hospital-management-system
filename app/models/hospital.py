from datetime import datetime
from app.models import db

class Hospital(db.Model):
    __tablename__ = 'hospitals'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    registration_number = db.Column(db.String(100), unique=True, nullable=False)
    hospital_type = db.Column(db.String(50), nullable=False) # 'Government', 'Private', 'Clinic', 'Speciality'
    address = db.Column(db.Text, nullable=False)
    state = db.Column(db.String(100), nullable=False)
    district = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    website = db.Column(db.String(150), nullable=True)
    logo_path = db.Column(db.String(255), default='default_hospital.png')
    license_document = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), default='Pending', nullable=False) # 'Pending', 'Approved', 'Rejected', 'Suspended'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    users = db.relationship('User', backref='hospital', lazy=True)
    appointments = db.relationship('Appointment', backref='hospital', lazy=True)
    rooms = db.relationship('Room', backref='hospital', lazy=True)
    bills = db.relationship('Bill', backref='hospital', lazy=True)
    departments = db.relationship('Department', backref='hospital', lazy=True)
    lab_tests = db.relationship('LabTest', backref='hospital', lazy=True)
    lab_packages = db.relationship('LabPackage', backref='hospital', lazy=True)
    lab_test_templates = db.relationship('LabTestTemplate', backref='hospital', lazy=True)
    lab_inventory = db.relationship('LabInventory', backref='hospital', lazy=True)

    def __repr__(self):
        return f"<Hospital {self.name}>"
