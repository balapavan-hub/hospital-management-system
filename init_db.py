import sys
from datetime import date
from app import create_app, db
from app.models.user import User, Patient, Doctor, Receptionist, LabTechnician
from app.models.department import Department
from app.models.setting import SystemSetting
from app.models.audit_log import AuditLog
from app.models.lab_test import LabTest, LabTestTemplate, LabPackage, LabInventory

def seed_database(app):
    with app.app_context():
        print("Starting Database Seeding...")
        print(f"Using database: {app.config['SQLALCHEMY_DATABASE_URI']}")
        
        # Detect and drop outdated lab schema to force recreation
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        if 'lab_tests' in inspector.get_table_names():
            columns = [c['name'] for c in inspector.get_columns('lab_tests')]
            if 'sample_id' not in columns:
                print("Outdated lab schema detected. Re-creating lab tables...")
                with db.engine.connect() as conn:
                    conn.execute(text("PRAGMA foreign_keys = OFF;"))
                    conn.execute(text("DROP TABLE IF EXISTS lab_package_tests;"))
                    conn.execute(text("DROP TABLE IF EXISTS lab_test_results;"))
                    conn.execute(text("DROP TABLE IF EXISTS lab_tests;"))
                    conn.execute(text("DROP TABLE IF EXISTS lab_packages;"))
                    conn.execute(text("DROP TABLE IF EXISTS lab_test_templates;"))
                    conn.execute(text("DROP TABLE IF EXISTS lab_inventory;"))
                    conn.execute(text("PRAGMA foreign_keys = ON;"))
                    conn.commit()
                print("Outdated lab tables dropped.")
                
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

        # 4. Seed Lab Technician User
        tech_user = User.query.filter_by(email="tech@hospital.com").first()
        if not tech_user:
            print("Seeding Lab Technician...")
            tech_u = User(email="tech@hospital.com", role="LabTechnician")
            tech_u.set_password("tech123")
            db.session.add(tech_u)
            db.session.commit()
            
            tech_p = LabTechnician(
                user_id=tech_u.id,
                first_name="Alex",
                last_name="Carter",
                phone="9876543211",
                employee_id="LT-1001"
            )
            db.session.add(tech_p)
            db.session.commit()
            print("Lab Tech account created (tech@hospital.com / tech123).")

        # 5. Seed Laboratory Test Templates (Parameters)
        if LabTestTemplate.query.count() == 0:
            print("Seeding Lab Parameter Templates...")
            templates = [
                LabTestTemplate(
                    test_name="Hemoglobin (Hb)", test_category="Hematology",
                    normal_range_min=12.0, normal_range_max=16.0, unit="g/dL",
                    age_min=0, age_max=120, gender="All", cost=150.0,
                    critical_range_min=7.0, critical_range_max=20.0
                ),
                LabTestTemplate(
                    test_name="Fasting Blood Sugar", test_category="Biochemistry",
                    normal_range_min=70.0, normal_range_max=100.0, unit="mg/dL",
                    age_min=0, age_max=120, gender="All", cost=100.0,
                    critical_range_min=50.0, critical_range_max=300.0
                ),
                LabTestTemplate(
                    test_name="TSH (Thyroid)", test_category="Endocrinology",
                    normal_range_min=0.4, normal_range_max=4.0, unit="uIU/mL",
                    age_min=0, age_max=120, gender="All", cost=350.0,
                    critical_range_min=0.1, critical_range_max=15.0
                ),
                LabTestTemplate(
                    test_name="Serum Creatinine", test_category="Renal",
                    normal_range_min=0.6, normal_range_max=1.2, unit="mg/dL",
                    age_min=0, age_max=120, gender="All", cost=200.0,
                    critical_range_min=0.3, critical_range_max=5.0
                ),
                LabTestTemplate(
                    test_name="HbA1c", test_category="Biochemistry",
                    normal_range_min=4.0, normal_range_max=5.6, unit="%",
                    age_min=0, age_max=120, gender="All", cost=280.0,
                    critical_range_min=3.5, critical_range_max=10.0
                )
            ]
            db.session.add_all(templates)
            db.session.commit()
            print(f"Seeded {len(templates)} lab test templates.")

        # 6. Seed Lab Packages
        if LabPackage.query.count() == 0:
            print("Seeding Lab Packages...")
            # Grab templates
            hb = LabTestTemplate.query.filter_by(test_name="Hemoglobin (Hb)").first()
            fbs = LabTestTemplate.query.filter_by(test_name="Fasting Blood Sugar").first()
            cr = LabTestTemplate.query.filter_by(test_name="Serum Creatinine").first()
            hba1c = LabTestTemplate.query.filter_by(test_name="HbA1c").first()
            
            p1 = LabPackage(name="Basic Health Checkup", description="Covers basic screening parameters for general wellness", cost=400.0)
            p1.templates = [hb, fbs, cr]
            db.session.add(p1)
            
            p2 = LabPackage(name="Diabetes Care Profile", description="Includes blood sugar & HbA1c glucose levels logs", cost=320.0)
            p2.templates = [fbs, hba1c]
            db.session.add(p2)
            
            db.session.commit()
            print("Seeded laboratory packages.")

        # 7. Seed Lab Inventory Items
        if LabInventory.query.count() == 0:
            print("Seeding Lab Inventory...")
            items = [
                LabInventory(item_name="EDTA Blood Vials", category="Reagents & Kits", quantity=150, unit="pcs", min_stock_level=50),
                LabInventory(item_name="Glucose Test Strips", category="Reagents & Kits", quantity=30, unit="boxes", min_stock_level=40), # Warn low stock!
                LabInventory(item_name="N95 Face Masks", category="PPE", quantity=300, unit="pcs", min_stock_level=100),
                LabInventory(item_name="Creatinine Reagent Kit", category="Chemicals", quantity=5, unit="kits", min_stock_level=2)
            ]
            db.session.add_all(items)
            db.session.commit()
            print("Seeded lab inventory items.")

        # 8. Seed Audit Logs
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
