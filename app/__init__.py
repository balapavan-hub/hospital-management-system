import os
from flask import Flask, session, g
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from config import Config
from app.models import db
from app.models.user import User

csrf = CSRFProtect()
login_manager = LoginManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize app with config folder creators
    config_class.init_app(app)

    # Initialize extensions
    db.init_app(app)
    csrf.init_app(app)
    
    # Auto-create tables and seed Super Admin on startup for seamless serverless deployment
    with app.app_context():
        try:
            db.create_all()
            admin_user = User.query.filter_by(role='SuperAdmin').first()
            if not admin_user:
                from app.models.setting import SystemSetting
                setting = SystemSetting(setting_key='hospital_name', setting_value='MediConnect India')
                db.session.add(setting)
                super_admin = User(email="admin@mediconnect.com", role="SuperAdmin")
                super_admin.set_password("admin123")
                db.session.add(super_admin)
                db.session.commit()
                print("Database tables and Super Admin successfully initialized.")
        except Exception as e:
            print("Database auto-initialization error:", e)
            
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    # User loader
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.doctor import doctor_bp
    from app.routes.patient import patient_bp
    from app.routes.receptionist import receptionist_bp
    from app.routes.lab_technician import lab_technician_bp
    from app.routes.super_admin import super_admin_bp
    from app.routes.nurse import nurse_bp
    from app.routes.pharmacist import pharmacist_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(doctor_bp, url_prefix='/doctor')
    app.register_blueprint(patient_bp, url_prefix='/patient')
    app.register_blueprint(receptionist_bp, url_prefix='/receptionist')
    app.register_blueprint(lab_technician_bp, url_prefix='/lab-technician')
    app.register_blueprint(super_admin_bp, url_prefix='/super-admin')
    app.register_blueprint(nurse_bp, url_prefix='/nurse')
    app.register_blueprint(pharmacist_bp, url_prefix='/pharmacist')

    # Context processors to inject global data
    @app.context_processor
    def inject_global_data():
        from flask_login import current_user
        from app.services.notification_service import NotificationService
        from app.models.setting import SystemSetting
        
        unread_notifications = []
        unread_count = 0
        current_theme = session.get('theme', 'light')
        
        if current_user and current_user.is_authenticated:
            unread_notifications = NotificationService.get_unread_notifications(current_user.id)
            unread_count = len(unread_notifications)
            
        # Get hospital name dynamically from database settings or logged in tenant
        hospital_name = "MediConnect India"
        if current_user and current_user.is_authenticated and current_user.hospital_id and current_user.hospital:
            hospital_name = current_user.hospital.name
        else:
            try:
                setting = SystemSetting.query.filter_by(setting_key='hospital_name').first()
                if setting:
                    hospital_name = setting.setting_value
            except Exception:
                pass
            
        return dict(
            unread_notifications=unread_notifications,
            unread_count=unread_count,
            current_theme=current_theme,
            hospital_name=hospital_name
        )

    return app
