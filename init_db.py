import sys
from app import create_app, db
from app.models.user import User
from app.models.setting import SystemSetting

def seed_database(app):
    with app.app_context():
        print("Starting Database Initialization...")
        print(f"Using database: {app.config['SQLALCHEMY_DATABASE_URI']}")
        
        # Drop all tables first for a clean migration to the SaaS multi-tenant schema
        print("Dropping all existing tables for a clean multi-tenant migration...")
        db.drop_all()
        db.create_all()
        print("Database tables created successfully.")

        # 1. Seed System Settings
        print("Seeding default settings...")
        setting = SystemSetting(setting_key='hospital_name', setting_value='MediConnect India')
        db.session.add(setting)
        db.session.commit()

        # 2. Seed Platform Super Admin (the ONLY pre-seeded credential)
        print("Creating Platform Super Admin...")
        super_admin = User(email="admin@mediconnect.com", role="SuperAdmin")
        super_admin.set_password("admin123")
        db.session.add(super_admin)
        db.session.commit()

        print("Database Initialization Completed!")
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
        print("  2. Hospitals register via the registration page")
        print("  3. Super Admin approves hospitals")
        print("  4. Super Admin creates admin credentials for each hospital")
        print("  5. Hospital Admin manages their own staff")
        print("=" * 50)

if __name__ == '__main__':
    app = create_app()
    seed_database(app)
