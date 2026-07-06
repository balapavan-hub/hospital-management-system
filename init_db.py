import sys
from datetime import date
from app import create_app, db
from app.models.user import User, Patient, Doctor, Receptionist
from app.models.department import Department
from app.models.setting import SystemSetting
from app.models.audit_log import AuditLog
from app.models.lab_test import LabTest

def seed_database(app):
    with app.app_context():
        print("Starting Database Seeding...")
        
        print(f"Using database: {app.config['SQLALCHEMY_DATABASE_URI']}")
        db.create_all()
        print("Database tables initialized successfully.")

        # 1. Seed System Settings
        if SystemSetting.query.filter_by(setting_key='hospital_name').first() is None:
            print("Seeding default hospital name setting...")
            setting = SystemSetting(setting_key='hospital_name', setting_value='Hospital Portal')
            db.session.add(setting)
            db.session.commit()

        # 2. Seed Departments if empty
        if Department.query.count() == 0:
            print("Seeding Departments...")
            depts = [
                Department(name="Cardiology", description="Expert care for heart disease, coronary interventions, and hypertension.", icon_name="bi-heart-pulse-fill"),
                Department(name="Orthopedics", description="Joint replacements, spine treatments, bone fractures, and physical therapy.", icon_name="bi-bone-fill"),
                Department(name="Neurology", description="Care for stroke, epilepsy, migraines, tremors, and brain disorders.", icon_name="bi-activity"),
                Department(name="Dermatology", description="Diagnosis and treatment of skin conditions, acne, eczema, and allergies.", icon_name="bi-sun-fill"),
                Department(name="Pediatrics", description="Comprehensive child health services, vaccinations, and growth reviews.", icon_name="bi-baby-carriage-fill"),
                Department(name="General Medicine", description="General OPD, chronic disease management, fevers, and medical checks.", icon_name="bi-shield-plus"),
                Department(name="ENT", description="Treatments for ear, nose, throat, sinuses, and hearing defects.", icon_name="bi-ear-fill"),
                Department(name="Dental", description="Teeth cleaning, root canals, dental crowns, and orthodontic care.", icon_name="bi-emoji-smile-fill"),
                Department(name="Gynecology", description="Maternal care, women's health, labor delivery, and screening.", icon_name="bi-gender-female"),
                Department(name="Emergency", description="24/7 immediate trauma care, emergency operations, and ICU care.", icon_name="bi-lightning-charge-fill")
            ]
            db.session.add_all(depts)
            db.session.commit()
            print(f"Seeded {len(depts)} departments.")
            
        # 3. Seed Admin Users
        admin_user = User.query.filter_by(email="admin@hospital.com").first()
        if not admin_user:
            print("Seeding Admin Users...")
            admin = User(email="admin@hospital.com", role="Admin")
            admin.set_password("admin123")
            db.session.add(admin)
            
            admin2 = User(email="admin@admin.com", role="Admin")
            admin2.set_password("admin123")
            db.session.add(admin2)
            db.session.commit()
            print("Admin accounts created (admin@hospital.com and admin@admin.com / admin123).")

        # 4. Seed Audit Logs
        if AuditLog.query.count() == 0:
            print("Seeding Audit Logs...")
            log = AuditLog(action="System initialization and clean seeding", ip_address="127.0.0.1")
            db.session.add(log)
            db.session.commit()
            print("Audit logs seeded.")

        print("Database Seeding Completed Successfully!")

if __name__ == "__main__":
    app = create_app()
    seed_database(app)
