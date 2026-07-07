from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import all models at the bottom to prevent circular imports and register them in metadata
from app.models.hospital import Hospital
from app.models.user import User, Patient, HospitalAdmin, Doctor, Nurse, Receptionist, LabTechnician, Pharmacist, BillingExecutive
from app.models.department import Department
from app.models.room import Room
from app.models.appointment import Appointment
from app.models.prescription import Prescription, PrescriptionMedicine
from app.models.billing import Bill, Payment
from app.models.medical_report import MedicalReport
from app.models.notification import Notification
from app.models.audit_log import AuditLog
from app.models.lab_test import LabTest, LabTestTemplate, LabPackage, LabInventory, LabTestResult
from app.models.pharmacy import Supplier, PharmacyMedicine, PharmacySale, PharmacyPurchase
from app.models.setting import SystemSetting
