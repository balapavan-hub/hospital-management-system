import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename

from app.models import db
from app.models.user import User, Patient, HospitalAdmin
from app.models.hospital import Hospital
from app.forms import (
    LoginForm, PatientRegisterForm, ForgotPasswordForm, 
    ResetPasswordForm, UpdateProfileForm, ChangePasswordForm, HospitalRegisterForm
)
from app.services import AuditService, NotificationService

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect_role_dashboard(current_user.role)
        
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact support.', 'danger')
                return render_template('auth/login.html', form=form)
                
            if user.hospital_id:
                hospital = Hospital.query.get(user.hospital_id)
                if hospital and hospital.status != 'Approved':
                    flash(f'Your hospital ("{hospital.name}") is currently {hospital.status}. Login is disabled until it is approved.', 'warning')
                    return render_template('auth/login.html', form=form)
                    
            login_user(user, remember=form.remember_me.data)
            
            # Audit log
            AuditService.log_action(user.id, "User Logged In", request.remote_addr)
            
            flash(f'Welcome back, {user.full_name}!', 'success')
            
            # Handle next parameter
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect_role_dashboard(user.role)
        else:
            flash('Invalid email or password.', 'danger')
            
    return render_template('auth/login.html', form=form)


@auth_bp.route('/register-hospital', methods=['GET', 'POST'])
def register_hospital():
    if current_user.is_authenticated:
        return redirect_role_dashboard(current_user.role)
        
    form = HospitalRegisterForm()
    if form.validate_on_submit():
        logo_filename = 'default_hospital.png'
        if form.logo.data:
            file = form.logo.data
            logo_filename = secure_filename(f"hospital_logo_{file.filename}")
            file.save(os.path.join(current_app.config['PROFILE_PICS_FOLDER'], logo_filename))
            
        license_filename = None
        if form.license_document.data:
            file = form.license_document.data
            license_filename = secure_filename(f"hospital_license_{file.filename}")
            file.save(os.path.join(current_app.config['REPORTS_FOLDER'], license_filename))
            
        # Create Hospital
        hospital = Hospital(
            name=form.hospital_name.data.strip(),
            registration_number=form.registration_number.data.strip(),
            hospital_type=form.hospital_type.data,
            address=form.address.data.strip(),
            state=form.state.data.strip(),
            district=form.district.data.strip(),
            city=form.city.data.strip(),
            pincode=form.pincode.data.strip(),
            email=form.email.data.strip(),
            phone=form.phone.data.strip(),
            website=form.website.data.strip() if form.website.data else None,
            logo_path=logo_filename,
            license_document=license_filename,
            status='Pending'
        )
        db.session.add(hospital)
        db.session.flush()
        
        # Create Hospital Admin User
        user = User(
            email=form.admin_email.data.strip(),
            role='HospitalAdmin',
            hospital_id=hospital.id
        )
        user.set_password(form.admin_password.data)
        db.session.add(user)
        db.session.flush()
        
        # Create Hospital Admin Profile
        hosp_admin = HospitalAdmin(
            user_id=user.id,
            hospital_id=hospital.id,
            first_name=form.admin_first_name.data.strip(),
            last_name=form.admin_last_name.data.strip(),
            phone=form.admin_phone.data.strip()
        )
        db.session.add(hosp_admin)
        db.session.commit()
        
        AuditService.log_action(user.id, f"Registered hospital '{hospital.name}' (Pending Super Admin approval)", request.remote_addr)
        flash('Hospital registration submitted successfully! Staff login will be activated once Platform Super Admin approves the hospital.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register_hospital.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect_role_dashboard(current_user.role)
        
    form = PatientRegisterForm()
    if form.validate_on_submit():
        # Create User
        user = User(email=form.email.data, role='Patient')
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush() # Populate user.id
        
        # Create Patient Profile
        patient = Patient(
            user_id=user.id,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data,
            gender=form.gender.data,
            date_of_birth=form.date_of_birth.data,
            blood_group=form.blood_group.data,
            address=form.address.data,
            medical_history=form.medical_history.data
        )
        db.session.add(patient)
        db.session.commit()
        
        # Log action and notify
        AuditService.log_action(user.id, "New Patient Registered via Portal", request.remote_addr)
        NotificationService.create_notification(
            user.id, 
            "Registration Successful", 
            "Welcome to MediCare! Your registration was successful. You can now book appointments."
        )
        
        flash('Registration successful! Please login to continue.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    AuditService.log_action(current_user.id, "User Logged Out", request.remote_addr)
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            # Simulate sending email
            flash(f"A password reset link has been sent to {form.email.data}. (For testing: use reset-password route directly)", 'info')
            return redirect(url_for('auth.login'))
        else:
            flash('No user found with that email address.', 'warning')
    return render_template('auth/forgot_password.html', form=form)


@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    form = ResetPasswordForm()
    if form.validate_on_submit():
        # In a real app, load user by token. Here, we allow a test reset by email.
        # Let's prompt for email in mock or just reset for a demo user.
        email = request.args.get('email') or 'patient@medicare.com'
        user = User.query.filter_by(email=email).first()
        if user:
            user.set_password(form.password.data)
            db.session.commit()
            AuditService.log_action(user.id, "Password Reset via Token", request.remote_addr)
            flash('Your password has been reset successfully. You can now login.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Invalid reset request.', 'danger')
    return render_template('auth/reset_password.html', form=form)


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    profile_form = UpdateProfileForm(current_user)
    password_form = ChangePasswordForm()
    
    # Pre-populate profile form
    if request.method == 'GET':
        profile_form.email.data = current_user.email
        if current_user.role == 'Patient' and current_user.patient:
            profile_form.phone.data = current_user.patient.phone
            profile_form.address.data = current_user.patient.address
            profile_form.medical_history.data = current_user.patient.medical_history
        elif current_user.role == 'Doctor' and current_user.doctor:
            profile_form.phone.data = current_user.doctor.phone
            profile_form.address.data = current_user.doctor.bio # Map bio to address for editing simplicity
        elif current_user.role == 'Receptionist' and current_user.receptionist:
            profile_form.phone.data = current_user.receptionist.phone
        elif current_user.role == 'LabTechnician' and current_user.lab_technician:
            profile_form.phone.data = current_user.lab_technician.phone

    # Handle Forms submission
    action = request.form.get('action')
    
    if action == 'update_profile' and profile_form.validate_on_submit():
        current_user.email = profile_form.email.data
        
        # Save photo if uploaded
        if profile_form.profile_photo.data:
            file = profile_form.profile_photo.data
            filename = secure_filename(f"user_{current_user.id}_{file.filename}")
            filepath = os.path.join(current_app.config['PROFILE_PICS_FOLDER'], filename)
            file.save(filepath)
            current_user.profile_photo = filename
            
        if current_user.role == 'Patient' and current_user.patient:
            current_user.patient.phone = profile_form.phone.data
            current_user.patient.address = profile_form.address.data
            current_user.patient.medical_history = profile_form.medical_history.data
        elif current_user.role == 'Doctor' and current_user.doctor:
            current_user.doctor.phone = profile_form.phone.data
            current_user.doctor.bio = profile_form.address.data
        elif current_user.role == 'Receptionist' and current_user.receptionist:
            current_user.receptionist.phone = profile_form.phone.data
        elif current_user.role == 'LabTechnician' and current_user.lab_technician:
            current_user.lab_technician.phone = profile_form.phone.data
            
        db.session.commit()
        AuditService.log_action(current_user.id, "Profile Updated", request.remote_addr)
        flash('Your profile has been updated successfully.', 'success')
        return redirect(url_for('auth.profile'))
        
    elif action == 'change_password' and password_form.validate_on_submit():
        if current_user.check_password(password_form.old_password.data):
            current_user.set_password(password_form.new_password.data)
            db.session.commit()
            AuditService.log_action(current_user.id, "Password Changed", request.remote_addr)
            flash('Your password has been changed successfully.', 'success')
            return redirect(url_for('auth.profile'))
        else:
            flash('Current password is incorrect.', 'danger')
            
    return render_template('auth/profile.html', profile_form=profile_form, password_form=password_form)


@auth_bp.route('/notifications/read/<int:id>')
@login_required
def read_notification(id):
    if NotificationService.mark_as_read(id):
        flash('Notification marked as read.', 'success')
    return redirect(request.referrer or url_for('main.index'))


@auth_bp.route('/notifications/read-all')
@login_required
def read_all_notifications():
    NotificationService.mark_all_as_read(current_user.id)
    flash('All notifications marked as read.', 'success')
    return redirect(request.referrer or url_for('main.index'))


def redirect_role_dashboard(role):
    """Helper function to redirect users to their respective dashboard blueprint."""
    if role == 'SuperAdmin':
        return redirect(url_for('super_admin.dashboard'))
    elif role == 'HospitalAdmin':
        return redirect(url_for('admin.dashboard'))
    elif role == 'Doctor':
        return redirect(url_for('doctor.dashboard'))
    elif role == 'Nurse':
        return redirect(url_for('nurse.dashboard'))
    elif role == 'Receptionist':
        return redirect(url_for('receptionist.dashboard'))
    elif role == 'LabTechnician':
        return redirect(url_for('lab_technician.dashboard'))
    elif role == 'Pharmacist':
        return redirect(url_for('pharmacist.dashboard'))
    elif role == 'BillingExecutive':
        return redirect(url_for('receptionist.dashboard')) # Billing executive shares Receptionist's portal
    elif role == 'Patient':
        return redirect(url_for('patient.dashboard'))
    return redirect(url_for('main.index'))
