import sys
from datetime import date
from app import create_app, db
from app.models.hospital import Hospital
from app.models.user import User, Patient, HospitalAdmin, Doctor, Nurse, Receptionist, LabTechnician, Pharmacist, BillingExecutive
from app.models.department import Department
from app.models.setting import SystemSetting
from app.models.lab_test import LabTest, LabTestTemplate, LabPackage, LabInventory
from app.models.pharmacy import PharmacyMedicine, Supplier

def seed_database(app):
    with app.app_context():
        print("Starting Database Seeding...")
        print(f"Using database: {app.config['SQLALCHEMY_DATABASE_URI']}")
        
        # Drop all tables first for a clean migration to the SaaS multi-tenant schema
        print("Dropping all existing tables for a clean multi-tenant migration...")
        db.drop_all()
        db.create_all()
        print("Database tables re-created successfully.")

        # 1. Seed System Settings
        print("Seeding default settings...")
        setting = SystemSetting(setting_key='hospital_name', setting_value='MediConnect India')
        db.session.add(setting)
        db.session.commit()

        # 2. Seed Partner Hospitals
        print("Seeding partner hospitals...")
        h1 = Hospital(
            name="Medicare General Hospital",
            registration_number="REG-MH-9921",
            hospital_type="Private",
            address="102 Marine Lines, Mumbai",
            state="Maharashtra",
            district="Mumbai",
            city="Mumbai",
            pincode="400002",
            email="contact@medicare-mumbai.org",
            phone="0224439129",
            website="https://medicare-mumbai.org",
            status="Approved"
        )
        h2 = Hospital(
            name="City Heart Clinic",
            registration_number="REG-KA-1122",
            hospital_type="Clinic",
            address="45 Jayanagar 4th Block, Bengaluru",
            state="Karnataka",
            district="Bengaluru",
            city="Bengaluru",
            pincode="560041",
            email="info@cityheart.org",
            phone="0802294819",
            status="Approved"
        )
        h3 = Hospital(
            name="Apollo Diagnostics Pune",
            registration_number="REG-MH-7711",
            hospital_type="Speciality Hospital",
            address="7 Bund Garden Road, Pune",
            state="Maharashtra",
            district="Pune",
            city="Pune",
            pincode="411001",
            email="pune@apollodiagnostics.org",
            phone="0209931818",
            status="Pending"
        )
        db.session.add_all([h1, h2, h3])
        db.session.commit()
        print("Hospitals seeded.")

        # 3. Seed Departments (For Hospital 1 and 2)
        print("Seeding Departments...")
        depts = [
            Department(hospital_id=h1.id, name="Cardiology", description="Expert care for heart disease, coronary interventions, and hypertension.", icon_name="bi-heart-pulse-fill"),
            Department(hospital_id=h1.id, name="Orthopedics", description="Joint replacements, spine treatments, bone fractures, and physical therapy.", icon_name="bi-bone-fill"),
            Department(hospital_id=h1.id, name="General Medicine", description="General OPD, chronic disease management, fevers, and medical checks.", icon_name="bi-shield-plus"),
            Department(hospital_id=h1.id, name="Pediatrics", description="Comprehensive child health services, vaccinations, and growth reviews.", icon_name="bi-baby-carriage-fill"),
            Department(hospital_id=h1.id, name="Gynecology", description="Maternal care, women's health, labor delivery, and screening.", icon_name="bi-gender-female"),
            Department(hospital_id=h1.id, name="Emergency", description="24/7 immediate trauma care, emergency operations, and ICU care.", icon_name="bi-lightning-charge-fill"),
            
            Department(hospital_id=h2.id, name="Cardiology", description="Expert care for heart disease, coronary interventions, and hypertension.", icon_name="bi-heart-pulse-fill"),
            Department(hospital_id=h2.id, name="General Medicine", description="General OPD, chronic disease management, fevers, and medical checks.", icon_name="bi-shield-plus")
        ]
        db.session.add_all(depts)
        db.session.commit()
        print("Departments seeded.")

        # 4. Seed Platform Super Admin
        print("Seeding Platform Super Admin...")
        super_admin = User(email="admin@mediconnect.com", role="SuperAdmin")
        super_admin.set_password("admin123")
        db.session.add(super_admin)

        # 5. Seed Hospital 1 Admin
        print("Seeding Hospital Admin...")
        hosp_admin_user = User(email="admin@hospital.com", role="HospitalAdmin", hospital_id=h1.id)
        hosp_admin_user.set_password("admin123")
        db.session.add(hosp_admin_user)
        db.session.flush()
        
        hosp_admin = HospitalAdmin(
            user_id=hosp_admin_user.id,
            hospital_id=h1.id,
            first_name="Medicare",
            last_name="Administrator",
            phone="9988776655"
        )
        db.session.add(hosp_admin)

        # 6. Seed Doctor
        print("Seeding Doctor...")
        dept_gm = Department.query.filter_by(hospital_id=h1.id, name="General Medicine").first()
        doc_user = User(email="doctor@hospital.com", role="Doctor", hospital_id=h1.id)
        doc_user.set_password("doctor123")
        db.session.add(doc_user)
        db.session.flush()
        
        doctor = Doctor(
            user_id=doc_user.id,
            hospital_id=h1.id,
            first_name="Vikas",
            last_name="Sharma",
            phone="9876543210",
            department_id=dept_gm.id,
            specialization="General Physician",
            qualification="MBBS, MD",
            consultation_fee=500.00,
            availability_status="Available"
        )
        db.session.add(doctor)

        # 7. Seed Nurse
        print("Seeding Nurse...")
        nurse_user = User(email="nurse@hospital.com", role="Nurse", hospital_id=h1.id)
        nurse_user.set_password("nurse123")
        db.session.add(nurse_user)
        db.session.flush()
        
        nurse = Nurse(
            user_id=nurse_user.id,
            hospital_id=h1.id,
            first_name="Priya",
            last_name="Nair",
            phone="9876543212"
        )
        db.session.add(nurse)

        # 8. Seed Receptionist
        print("Seeding Receptionist...")
        recep_user = User(email="recep@hospital.com", role="Receptionist", hospital_id=h1.id)
        recep_user.set_password("recep123")
        db.session.add(recep_user)
        db.session.flush()
        
        recep = Receptionist(
            user_id=recep_user.id,
            hospital_id=h1.id,
            first_name="Rohan",
            last_name="Mehta",
            phone="9876543213",
            shift="Day"
        )
        db.session.add(recep)

        # 9. Seed Lab Technician
        print("Seeding Lab Technician...")
        tech_user = User(email="tech@hospital.com", role="LabTechnician", hospital_id=h1.id)
        tech_user.set_password("tech123")
        db.session.add(tech_user)
        db.session.flush()
        
        tech = LabTechnician(
            user_id=tech_user.id,
            hospital_id=h1.id,
            first_name="Alex",
            last_name="Carter",
            phone="9876543211",
            employee_id="LT-1001"
        )
        db.session.add(tech)

        # 10. Seed Pharmacist
        print("Seeding Pharmacist...")
        pharm_user = User(email="pharmacist@hospital.com", role="Pharmacist", hospital_id=h1.id)
        pharm_user.set_password("pharmacist123")
        db.session.add(pharm_user)
        db.session.flush()
        
        pharm = Pharmacist(
            user_id=pharm_user.id,
            hospital_id=h1.id,
            first_name="Karan",
            last_name="Malhotra",
            phone="9876543214"
        )
        db.session.add(pharm)

        # 11. Seed Billing Executive
        print("Seeding Billing Executive...")
        billing_user = User(email="billing@hospital.com", role="BillingExecutive", hospital_id=h1.id)
        billing_user.set_password("billing123")
        db.session.add(billing_user)
        db.session.flush()
        
        bill_exec = BillingExecutive(
            user_id=billing_user.id,
            hospital_id=h1.id,
            first_name="Deepa",
            last_name="Joshi",
            phone="9876543215"
        )
        db.session.add(bill_exec)

        # 12. Seed Patient
        print("Seeding Patient...")
        patient_user = User(email="patient@mediconnect.com", role="Patient")
        patient_user.set_password("patient123")
        db.session.add(patient_user)
        db.session.flush()
        
        patient = Patient(
            user_id=patient_user.id,
            first_name="Amit",
            last_name="Patel",
            phone="9876543216",
            gender="Male",
            date_of_birth=date(1992, 4, 15),
            blood_group="O+"
        )
        db.session.add(patient)

        # 13. Seed Laboratory Test Templates (Parameters)
        print("Seeding Lab Parameters...")
        templates = [
            LabTestTemplate(
                hospital_id=h1.id,
                test_name="Hemoglobin (Hb)", test_category="Hematology",
                normal_range_min=12.0, normal_range_max=16.0, unit="g/dL",
                age_min=0, age_max=120, gender="All", cost=150.0,
                critical_range_min=7.0, critical_range_max=20.0
            ),
            LabTestTemplate(
                hospital_id=h1.id,
                test_name="Fasting Blood Sugar", test_category="Biochemistry",
                normal_range_min=70.0, normal_range_max=100.0, unit="mg/dL",
                age_min=0, age_max=120, gender="All", cost=100.0,
                critical_range_min=50.0, critical_range_max=300.0
            ),
            LabTestTemplate(
                hospital_id=h1.id,
                test_name="HbA1c", test_category="Biochemistry",
                normal_range_min=4.0, normal_range_max=5.6, unit="%",
                age_min=0, age_max=120, gender="All", cost=280.0,
                critical_range_min=3.5, critical_range_max=10.0
            )
        ]
        db.session.add_all(templates)
        db.session.commit()

        # 14. Seed Lab Packages
        print("Seeding Lab Packages...")
        hb = LabTestTemplate.query.filter_by(hospital_id=h1.id, test_name="Hemoglobin (Hb)").first()
        fbs = LabTestTemplate.query.filter_by(hospital_id=h1.id, test_name="Fasting Blood Sugar").first()
        hba1c = LabTestTemplate.query.filter_by(hospital_id=h1.id, test_name="HbA1c").first()
        
        p1 = LabPackage(hospital_id=h1.id, name="Basic Health Checkup", description="Basic general wellness screen", cost=400.0)
        p1.templates = [hb, fbs]
        p2 = LabPackage(hospital_id=h1.id, name="Diabetes Care Profile", description="Includes Fasting Blood Sugar & HbA1c screening", cost=320.0)
        p2.templates = [fbs, hba1c]
        db.session.add_all([p1, p2])

        # 15. Seed Lab Inventory
        print("Seeding Lab Inventory...")
        inv = [
            LabInventory(hospital_id=h1.id, item_name="Hemoglobin Reagent", category="Chemicals", quantity=100, unit="vials", min_stock_level=15),
            LabInventory(hospital_id=h1.id, item_name="Surgical Gloves (M)", category="Consumables", quantity=250, unit="pairs", min_stock_level=50)
        ]
        db.session.add_all(inv)

        # 16. Seed Pharmacy Medicines & Suppliers
        print("Seeding Pharmacy Suppliers & Medicines...")
        supplier = Supplier(
            hospital_id=h1.id,
            name="Apex Pharmaceutical Distributors",
            contact_person="Ramesh Kumar",
            phone="9128381981",
            email="sales@apexpharma.in",
            address="3A Industrial Area Phase-2, Mumbai"
        )
        db.session.add(supplier)
        db.session.flush()

        meds = [
            PharmacyMedicine(
                hospital_id=h1.id,
                item_name="Paracetamol 650mg (Dolo)",
                category="Tablet",
                quantity=500,
                unit="tablets",
                min_stock_level=50,
                purchase_price=1.20,
                selling_price=2.00,
                expiry_date=date(2028, 12, 31),
                supplier_id=supplier.id
            ),
            PharmacyMedicine(
                hospital_id=h1.id,
                item_name="Amoxicillin 500mg",
                category="Capsule",
                quantity=200,
                unit="capsules",
                min_stock_level=30,
                purchase_price=4.50,
                selling_price=8.00,
                expiry_date=date(2027, 6, 30),
                supplier_id=supplier.id
            )
        ]
        db.session.add_all(meds)
        
        db.session.commit()
        print("Database Seeding Completed Successfully!")
