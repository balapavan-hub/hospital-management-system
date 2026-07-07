import sys
from datetime import date
from app import create_app, db
from app.models.hospital import Hospital
from app.models.user import User, HospitalAdmin
from app.models.setting import SystemSetting

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

        # 2. Seed Partner Hospitals (all in Pending status - Super Admin must approve)
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
            status="Pending"
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
            status="Pending"
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

        # 3. Seed Platform Super Admin (the ONLY pre-seeded credential)
        print("Seeding Platform Super Admin...")
        super_admin = User(email="admin@mediconnect.com", role="SuperAdmin")
        super_admin.set_password("admin123")
        db.session.add(super_admin)
        db.session.commit()

        print("Database Seeding Completed Successfully!")
        print("")
        print("=" * 50)
        print("  PLATFORM SUPER ADMIN CREDENTIALS")
        print("=" * 50)
        print("  Email   : admin@mediconnect.com")
        print("  Password: admin123")
        print("=" * 50)
        print("")
        print("WORKFLOW:")
        print("  1. Login as Super Admin")
        print("  2. Approve a hospital from Manage Hospitals")
        print("  3. Click 'Set Admin' to create admin credentials")
        print("  4. Hospital Admin can then add their staff")
        print("=" * 50)

if __name__ == '__main__':
    app = create_app()
    seed_database(app)
