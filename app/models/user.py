from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import db

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('Admin', 'Doctor', 'Receptionist', 'Patient', 'LabTechnician', name='user_roles'), nullable=False)
    profile_photo = db.Column(db.String(255), default='default_profile.png')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    patient = db.relationship('Patient', backref='user', uselist=False, cascade="all, delete-orphan")
    doctor = db.relationship('Doctor', backref='user', uselist=False, cascade="all, delete-orphan")
    receptionist = db.relationship('Receptionist', backref='user', uselist=False, cascade="all, delete-orphan")
    lab_technician = db.relationship('LabTechnician', backref='user', uselist=False, cascade="all, delete-orphan")
    notifications = db.relationship('Notification', backref='user', cascade="all, delete-orphan")
    audit_logs = db.relationship('AuditLog', backref='user', cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        if self.role == 'Patient' and self.patient:
            return f"{self.patient.first_name} {self.patient.last_name}"
        elif self.role == 'Doctor' and self.doctor:
            return f"Dr. {self.doctor.first_name} {self.doctor.last_name}"
        elif self.role == 'Receptionist' and self.receptionist:
            return f"{self.receptionist.first_name} {self.receptionist.last_name}"
        elif self.role == 'LabTechnician' and self.lab_technician:
            return f"{self.lab_technician.first_name} {self.lab_technician.last_name}"
        return "Administrator"

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class Patient(db.Model):
    __tablename__ = 'patients'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    blood_group = db.Column(db.String(5), nullable=True)
    address = db.Column(db.Text, nullable=True)
    medical_history = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    appointments = db.relationship('Appointment', backref='patient', cascade="all, delete-orphan")
    prescriptions = db.relationship('Prescription', backref='patient', cascade="all, delete-orphan")
    bills = db.relationship('Bill', backref='patient', cascade="all, delete-orphan")
    medical_reports = db.relationship('MedicalReport', backref='patient', cascade="all, delete-orphan")
    lab_tests = db.relationship('LabTest', backref='patient', cascade="all, delete-orphan")

    @property
    def age(self):
        today = datetime.today()
        dob = self.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<Patient {self.full_name}>"


class Doctor(db.Model):
    __tablename__ = 'doctors'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id', ondelete='RESTRICT'), nullable=False)
    specialization = db.Column(db.String(100), nullable=False)
    qualification = db.Column(db.String(100), nullable=False)
    consultation_fee = db.Column(db.Numeric(10, 2), nullable=False, default=500.00)
    bio = db.Column(db.Text, nullable=True)
    availability_status = db.Column(db.String(50), default='Available') # Available, On Leave, Busy
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    appointments = db.relationship('Appointment', backref='doctor', cascade="all, delete-orphan")
    prescriptions = db.relationship('Prescription', backref='doctor', cascade="all, delete-orphan")
    medical_reports = db.relationship('MedicalReport', backref='doctor')
    lab_tests = db.relationship('LabTest', backref='doctor')

    @property
    def full_name(self):
        return f"Dr. {self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<Doctor {self.full_name}>"


class Receptionist(db.Model):
    __tablename__ = 'receptionists'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    shift = db.Column(db.String(50), default='Day') # Day, Evening, Night
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<Receptionist {self.full_name}>"


class LabTechnician(db.Model):
    __tablename__ = 'lab_technicians'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    employee_id = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    lab_tests = db.relationship('LabTest', backref='lab_technician')

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<LabTechnician {self.full_name}>"

