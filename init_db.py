import sys
from app import create_app, db
from app.models.user import User
from app.models.setting import SystemSetting

def seed_database(app):
    with app.app_context():
        # Only initialize if the database is empty (first run)
        # Check if the Super Admin already exists — if yes, skip seeding
        db.create_all()
        
        existing_admin = User.query.filter_by(role='SuperAdmin').first()
        if existing_admin:
            print("Database already initialized. Skipping seed.")
            return
        
        print("First run detected — initializing database...")

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
