from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import db
from app.models.hospital import Hospital
from app.models.user import User, Patient, Doctor, HospitalAdmin
from app.models.audit_log import AuditLog
from app.models.appointment import Appointment
from app.models.billing import Bill
from app.services.audit_service import AuditService

super_admin_bp = Blueprint('super_admin', __name__)

@super_admin_bp.before_request
@login_required
def super_admin_required():
    if current_user.role != 'SuperAdmin':
        flash('Unauthorized access! Platform Super Admin credentials required.', 'danger')
        return redirect(url_for('auth.login'))

@super_admin_bp.route('/dashboard')
def dashboard():
    # Metrics
    total_hospitals = Hospital.query.count()
    pending_hospitals = Hospital.query.filter_by(status='Pending').count()
    approved_hospitals = Hospital.query.filter_by(status='Approved').count()
    suspended_hospitals = Hospital.query.filter_by(status='Suspended').count()
    
    total_patients = Patient.query.count()
    total_doctors = Doctor.query.count()
    
    # Platform Analytics
    total_revenue = float(db.session.query(db.func.sum(Bill.grand_total)).filter_by(status='Paid').scalar() or 0.0)
    total_appointments = Appointment.query.count()

    # Recent hospital registrations
    recent_registrations = Hospital.query.order_by(Hospital.created_at.desc()).limit(5).all()
    recent_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(10).all()

    # Geographical breakdown
    cities_list = db.session.query(Hospital.city, db.func.count(Hospital.id)).group_by(Hospital.city).all()
    states_list = db.session.query(Hospital.state, db.func.count(Hospital.id)).group_by(Hospital.state).all()

    return render_template(
        'super_admin/dashboard.html',
        total_hospitals=total_hospitals,
        pending_hospitals=pending_hospitals,
        approved_hospitals=approved_hospitals,
        suspended_hospitals=suspended_hospitals,
        total_patients=total_patients,
        total_doctors=total_doctors,
        total_revenue=total_revenue,
        total_appointments=total_appointments,
        recent_registrations=recent_registrations,
        recent_logs=recent_logs,
        cities_list=cities_list,
        states_list=states_list
    )

@super_admin_bp.route('/hospitals')
def hospitals():
    status_filter = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)
    
    query = Hospital.query
    if status_filter:
        query = query.filter_by(status=status_filter)
        
    pagination = query.order_by(Hospital.created_at.desc()).paginate(page=page, per_page=10)
    return render_template('super_admin/hospitals.html', pagination=pagination, status_filter=status_filter)

@super_admin_bp.route('/hospitals/status/<int:id>/<string:new_status>', methods=['POST'])
def change_hospital_status(id, new_status):
    if new_status not in ['Approved', 'Rejected', 'Suspended']:
        flash('Invalid status change request.', 'danger')
        return redirect(url_for('super_admin.hospitals'))
        
    hospital = Hospital.query.get_or_404(id)
    old_status = hospital.status
    hospital.status = new_status
    
    # Suspend/Activate corresponding users
    users = User.query.filter_by(hospital_id=id).all()
    for u in users:
        u.is_active = (new_status == 'Approved')
        
    db.session.commit()
    AuditService.log_action(current_user.id, f"Changed Hospital status for '{hospital.name}' from {old_status} to {new_status}", request.remote_addr)
    flash(f"Hospital '{hospital.name}' status successfully updated to {new_status}.", 'success')
    return redirect(url_for('super_admin.hospitals'))

@super_admin_bp.route('/audit-logs')
def audit_logs():
    page = request.args.get('page', 1, type=int)
    pagination = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('super_admin/audit_logs.html', pagination=pagination)

@super_admin_bp.route('/hospitals/<int:id>/create-admin', methods=['GET', 'POST'])
def create_admin(id):
    hospital = Hospital.query.get_or_404(id)
    if hospital.status != 'Approved':
        flash('Admin credentials can only be set for approved hospitals.', 'danger')
        return redirect(url_for('super_admin.hospitals'))
        
    if hospital.admin_user:
        flash('This hospital already has an administrator user.', 'warning')
        return redirect(url_for('super_admin.hospitals'))

    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '').strip()

        if not (first_name and last_name and email and phone and password):
            flash('All fields are required to create administrator credentials.', 'danger')
            return render_template('super_admin/create_admin.html', hospital=hospital)

        # Check duplicate email
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email address is already in use by another user.', 'danger')
            return render_template('super_admin/create_admin.html', hospital=hospital)

        # Create user
        user = User(email=email, role='HospitalAdmin', hospital_id=hospital.id)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        # Create admin profile
        admin_profile = HospitalAdmin(
            user_id=user.id,
            hospital_id=hospital.id,
            first_name=first_name,
            last_name=last_name,
            phone=phone
        )
        db.session.add(admin_profile)
        db.session.commit()

        AuditService.log_action(current_user.id, f"Created admin credentials for hospital '{hospital.name}' (User ID: {user.id})", request.remote_addr)
        flash(f"Administrator credentials for '{hospital.name}' created successfully!", 'success')
        return redirect(url_for('super_admin.hospitals'))

    return render_template('super_admin/create_admin.html', hospital=hospital)
