from datetime import datetime, date
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, Response
from flask_login import login_required, current_user
from sqlalchemy import func

from app.models import db
from app.models.user import User, Doctor, Patient, Receptionist, LabTechnician, Nurse, Pharmacist, BillingExecutive
from app.models.department import Department
from app.models.appointment import Appointment
from app.models.billing import Bill, Payment
from app.models.room import Room
from app.models.audit_log import AuditLog
from app.models.lab_test import LabTest, LabPackage, LabTestTemplate, LabInventory
from app.forms import (
    DoctorForm, ReceptionistForm, DepartmentForm, RoomForm, 
    LabPackageForm, LabTestTemplateForm, LabTechnicianForm,
    NurseForm, PharmacistForm, BillingExecutiveForm
)
from app.services import AuditService, ReportService

admin_bp = Blueprint('admin', __name__)

# Middleware to ensure only Hospital Admins can access this blueprint
@admin_bp.before_request
@login_required
def admin_required():
    if current_user.role != 'HospitalAdmin':
        flash('Unauthorized access! Hospital Admin credentials required.', 'danger')
        return redirect(url_for('auth.login'))

@admin_bp.route('/dashboard')
def dashboard():
    h_id = current_user.hospital_id
    
    # Staff Counts
    total_doctors = Doctor.query.filter_by(hospital_id=h_id).count()
    total_receptionists = Receptionist.query.filter_by(hospital_id=h_id).count()
    total_technicians = LabTechnician.query.filter_by(hospital_id=h_id).count()
    total_nurses = Nurse.query.filter_by(hospital_id=h_id).count()
    total_pharmacists = Pharmacist.query.filter_by(hospital_id=h_id).count()
    total_executives = BillingExecutive.query.filter_by(hospital_id=h_id).count()
    
    # Patients who have visited this hospital
    total_patients = Patient.query.join(Appointment).filter(Appointment.hospital_id == h_id).distinct().count()
    
    today_str = date.today()
    today_appointments = Appointment.query.filter_by(hospital_id=h_id, appointment_date=today_str).count()
    available_docs_count = Doctor.query.filter_by(hospital_id=h_id, availability_status='Available').count()
    
    # Revenue calculations
    total_revenue = float(db.session.query(func.sum(Bill.grand_total)).filter_by(hospital_id=h_id, status='Paid').scalar() or 0.0)
    
    recent_appointments = Appointment.query.filter_by(hospital_id=h_id).order_by(Appointment.created_at.desc()).limit(5).all()
    recent_logs = AuditLog.query.filter_by(hospital_id=h_id).order_by(AuditLog.created_at.desc()).limit(5).all()
    
    return render_template(
        'admin/dashboard.html',
        total_doctors=total_doctors,
        total_receptionists=total_receptionists,
        total_technicians=total_technicians,
        total_nurses=total_nurses,
        total_pharmacists=total_pharmacists,
        total_executives=total_executives,
        total_patients=total_patients,
        today_appointments=today_appointments,
        available_docs_count=available_docs_count,
        total_revenue=total_revenue,
        recent_appointments=recent_appointments,
        recent_logs=recent_logs
    )

# ----------------------------------------------------
# STAFF MANAGEMENT
# ----------------------------------------------------

@admin_bp.route('/doctors')
def doctors():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    query = Doctor.query.filter_by(hospital_id=current_user.hospital_id)
    if search:
        query = query.filter(
            (Doctor.first_name.ilike(f'%{search}%')) |
            (Doctor.last_name.ilike(f'%{search}%')) |
            (Doctor.specialization.ilike(f'%{search}%'))
        )
    pagination = query.order_by(Doctor.first_name.asc()).paginate(page=page, per_page=10)
    return render_template('admin/doctors.html', pagination=pagination, search=search)

@admin_bp.route('/doctors/add', methods=['GET', 'POST'])
def add_doctor():
    form = DoctorForm()
    # Populate departments dropdown from hospital departments
    form.department_id.choices = [(d.id, d.name) for d in Department.query.filter_by(hospital_id=current_user.hospital_id).all()]
    print(f"DEBUG: Logged in user: {current_user.email}, Hospital ID: {current_user.hospital_id}")
    print(f"DEBUG: Form department choices: {form.department_id.choices}")
    
    if form.validate_on_submit():
        user = User(email=form.email.data, role='Doctor', hospital_id=current_user.hospital_id)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()
        
        doctor = Doctor(
            user_id=user.id,
            hospital_id=current_user.hospital_id,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data,
            department_id=form.department_id.data,
            specialization=form.specialization.data,
            qualification=form.qualification.data,
            consultation_fee=form.consultation_fee.data,
            bio=form.bio.data,
            availability_status=form.availability_status.data
        )
        db.session.add(doctor)
        db.session.commit()
        
        AuditService.log_action(current_user.id, f"Added Doctor '{doctor.full_name}'", request.remote_addr, current_user.hospital_id)
        flash('Doctor added successfully!', 'success')
        return redirect(url_for('admin.doctors'))
        
    return render_template('admin/doctor_form.html', form=form, title="Add Doctor")

@admin_bp.route('/doctors/edit/<int:id>', methods=['GET', 'POST'])
def edit_doctor(id):
    doctor = Doctor.query.filter_by(id=id, hospital_id=current_user.hospital_id).first_or_404()
    user = User.query.get(doctor.user_id)
    
    form = DoctorForm(doctor_id=doctor.id)
    form.department_id.choices = [(d.id, d.name) for d in Department.query.filter_by(hospital_id=current_user.hospital_id).all()]
    
    if form.validate_on_submit():
        user.email = form.email.data
        if form.password.data:
            user.set_password(form.password.data)
            
        doctor.first_name = form.first_name.data
        doctor.last_name = form.last_name.data
        doctor.phone = form.phone.data
        doctor.department_id = form.department_id.data
        doctor.specialization = form.specialization.data
        doctor.qualification = form.qualification.data
        doctor.consultation_fee = form.consultation_fee.data
        doctor.bio = form.bio.data
        doctor.availability_status = form.availability_status.data
        
        db.session.commit()
        AuditService.log_action(current_user.id, f"Updated Doctor '{doctor.full_name}'", request.remote_addr, current_user.hospital_id)
        flash('Doctor updated successfully!', 'success')
        return redirect(url_for('admin.doctors'))
        
    # Populate form values for GET
    if request.method == 'GET':
        form.first_name.data = doctor.first_name
        form.last_name.data = doctor.last_name
        form.email.data = user.email
        form.phone.data = doctor.phone
        form.department_id.data = doctor.department_id
        form.specialization.data = doctor.specialization
        form.qualification.data = doctor.qualification
        form.consultation_fee.data = doctor.consultation_fee
        form.bio.data = doctor.bio
        form.availability_status.data = doctor.availability_status
        
    return render_template('admin/doctor_form.html', form=form, title="Edit Doctor")

@admin_bp.route('/doctors/delete/<int:id>', methods=['POST'])
def delete_doctor(id):
    doctor = Doctor.query.filter_by(id=id, hospital_id=current_user.hospital_id).first_or_404()
    user = User.query.get(doctor.user_id)
    
    AuditService.log_action(current_user.id, f"Deleted Doctor '{doctor.full_name}'", request.remote_addr, current_user.hospital_id)
    db.session.delete(user)
    db.session.commit()
    
    flash('Doctor deleted successfully.', 'success')
    return redirect(url_for('admin.doctors'))

# -- RECEPTIONISTS --
@admin_bp.route('/receptionists')
def receptionists():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    query = Receptionist.query.filter_by(hospital_id=current_user.hospital_id)
    if search:
        query = query.filter(
            (Receptionist.first_name.ilike(f'%{search}%')) |
            (Receptionist.last_name.ilike(f'%{search}%'))
        )
    pagination = query.order_by(Receptionist.first_name.asc()).paginate(page=page, per_page=10)
    return render_template('admin/receptionists.html', pagination=pagination, search=search)

@admin_bp.route('/receptionists/add', methods=['GET', 'POST'])
def add_receptionist():
    form = ReceptionistForm()
    if form.validate_on_submit():
        user = User(email=form.email.data, role='Receptionist', hospital_id=current_user.hospital_id)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()
        
        rec = Receptionist(
            user_id=user.id,
            hospital_id=current_user.hospital_id,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data,
            shift=form.shift.data
        )
        db.session.add(rec)
        db.session.commit()
        
        AuditService.log_action(current_user.id, f"Added Receptionist '{rec.full_name}'", request.remote_addr, current_user.hospital_id)
        flash('Receptionist added successfully!', 'success')
        return redirect(url_for('admin.receptionists'))
        
    return render_template('admin/receptionist_form.html', form=form, title="Add Receptionist")

@admin_bp.route('/receptionists/edit/<int:id>', methods=['GET', 'POST'])
def edit_receptionist(id):
    rec = Receptionist.query.filter_by(id=id, hospital_id=current_user.hospital_id).first_or_404()
    user = User.query.get(rec.user_id)
    
    form = ReceptionistForm(receptionist_id=rec.id)
    if form.validate_on_submit():
        user.email = form.email.data
        if form.password.data:
            user.set_password(form.password.data)
            
        rec.first_name = form.first_name.data
        rec.last_name = form.last_name.data
        rec.phone = form.phone.data
        rec.shift = form.shift.data
        
        db.session.commit()
        AuditService.log_action(current_user.id, f"Updated Receptionist '{rec.full_name}'", request.remote_addr, current_user.hospital_id)
        flash('Receptionist updated successfully!', 'success')
        return redirect(url_for('admin.receptionists'))
        
    if request.method == 'GET':
        form.first_name.data = rec.first_name
        form.last_name.data = rec.last_name
        form.email.data = user.email
        form.phone.data = rec.phone
        form.shift.data = rec.shift
        
    return render_template('admin/receptionist_form.html', form=form, title="Edit Receptionist")

@admin_bp.route('/receptionists/delete/<int:id>', methods=['POST'])
def delete_receptionist(id):
    rec = Receptionist.query.filter_by(id=id, hospital_id=current_user.hospital_id).first_or_404()
    user = User.query.get(rec.user_id)
    
    AuditService.log_action(current_user.id, f"Deleted Receptionist '{rec.full_name}'", request.remote_addr, current_user.hospital_id)
    db.session.delete(user)
    db.session.commit()
    
    flash('Receptionist deleted successfully.', 'success')
    return redirect(url_for('admin.receptionists'))

# -- LAB TECHNICIANS --
@admin_bp.route('/lab-technicians')
def lab_technicians():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    query = LabTechnician.query.filter_by(hospital_id=current_user.hospital_id)
    if search:
        query = query.filter(
            (LabTechnician.first_name.ilike(f'%{search}%')) |
            (LabTechnician.last_name.ilike(f'%{search}%'))
        )
    pagination = query.order_by(LabTechnician.first_name.asc()).paginate(page=page, per_page=10)
    return render_template('admin/lab_technicians.html', pagination=pagination, search=search)

@admin_bp.route('/lab-technicians/add', methods=['GET', 'POST'])
def add_lab_technician():
    form = LabTechnicianForm()
    if form.validate_on_submit():
        user = User(email=form.email.data, role='LabTechnician', hospital_id=current_user.hospital_id)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()
        
        tech = LabTechnician(
            user_id=user.id,
            hospital_id=current_user.hospital_id,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data,
            employee_id=form.employee_id.data
        )
        db.session.add(tech)
        db.session.commit()
        
        AuditService.log_action(current_user.id, f"Added Lab Technician '{tech.full_name}'", request.remote_addr, current_user.hospital_id)
        flash('Lab Technician added successfully!', 'success')
        return redirect(url_for('admin.lab_technicians'))
        
    return render_template('admin/lab_technician_form.html', form=form, title="Add Lab Technician")

@admin_bp.route('/lab-technicians/edit/<int:id>', methods=['GET', 'POST'])
def edit_lab_technician(id):
    tech = LabTechnician.query.filter_by(id=id, hospital_id=current_user.hospital_id).first_or_404()
    user = User.query.get(tech.user_id)
    
    form = LabTechnicianForm(technician_id=tech.id)
    if form.validate_on_submit():
        user.email = form.email.data
        if form.password.data:
            user.set_password(form.password.data)
            
        tech.first_name = form.first_name.data
        tech.last_name = form.last_name.data
        tech.phone = form.phone.data
        tech.employee_id = form.employee_id.data
        
        db.session.commit()
        AuditService.log_action(current_user.id, f"Updated Lab Technician '{tech.full_name}'", request.remote_addr, current_user.hospital_id)
        flash('Lab Technician updated successfully!', 'success')
        return redirect(url_for('admin.lab_technicians'))
        
    if request.method == 'GET':
        form.first_name.data = tech.first_name
        form.last_name.data = tech.last_name
        form.email.data = user.email
        form.phone.data = tech.phone
        form.employee_id.data = tech.employee_id
        
    return render_template('admin/lab_technician_form.html', form=form, title="Edit Lab Technician")

@admin_bp.route('/lab-technicians/delete/<int:id>', methods=['POST'])
def delete_lab_technician(id):
    tech = LabTechnician.query.filter_by(id=id, hospital_id=current_user.hospital_id).first_or_404()
    user = User.query.get(tech.user_id)
    
    AuditService.log_action(current_user.id, f"Deleted Lab Technician '{tech.full_name}'", request.remote_addr, current_user.hospital_id)
    db.session.delete(user)
    db.session.commit()
    
    flash('Lab Technician deleted successfully.', 'success')
    return redirect(url_for('admin.lab_technicians'))

# -- NURSES --
@admin_bp.route('/nurses')
def nurses():
    nurses_list = Nurse.query.filter_by(hospital_id=current_user.hospital_id).all()
    return render_template('admin/nurses.html', nurses=nurses_list)

@admin_bp.route('/nurses/add', methods=['GET', 'POST'])
def add_nurse():
    form = NurseForm()
    if form.validate_on_submit():
        user = User(email=form.email.data, role='Nurse', hospital_id=current_user.hospital_id)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()
        
        nurse = Nurse(
            user_id=user.id,
            hospital_id=current_user.hospital_id,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data
        )
        db.session.add(nurse)
        db.session.commit()
        
        AuditService.log_action(current_user.id, f"Added Nurse '{nurse.full_name}'", request.remote_addr, current_user.hospital_id)
        flash('Nurse registered successfully!', 'success')
        return redirect(url_for('admin.nurses'))
        
    return render_template('admin/nurse_form.html', form=form, title="Add Nurse")

@admin_bp.route('/nurses/edit/<int:id>', methods=['GET', 'POST'])
def edit_nurse(id):
    nurse = Nurse.query.filter_by(id=id, hospital_id=current_user.hospital_id).first_or_404()
    user = User.query.get(nurse.user_id)
    
    form = NurseForm(nurse_id=nurse.id)
    if form.validate_on_submit():
        user.email = form.email.data
        if form.password.data:
            user.set_password(form.password.data)
        nurse.first_name = form.first_name.data
        nurse.last_name = form.last_name.data
        nurse.phone = form.phone.data
        db.session.commit()
        
        AuditService.log_action(current_user.id, f"Updated Nurse '{nurse.full_name}'", request.remote_addr, current_user.hospital_id)
        flash('Nurse details updated successfully!', 'success')
        return redirect(url_for('admin.nurses'))
        
    if request.method == 'GET':
        form.first_name.data = nurse.first_name
        form.last_name.data = nurse.last_name
        form.email.data = user.email
        form.phone.data = nurse.phone
        
    return render_template('admin/nurse_form.html', form=form, title="Edit Nurse")

@admin_bp.route('/nurses/delete/<int:id>', methods=['POST'])
def delete_nurse(id):
    nurse = Nurse.query.filter_by(id=id, hospital_id=current_user.hospital_id).first_or_404()
    user = User.query.get(nurse.user_id)
    db.session.delete(user)
    db.session.commit()
    flash('Nurse profile deleted successfully.', 'success')
    return redirect(url_for('admin.nurses'))

# -- PHARMACISTS --
@admin_bp.route('/pharmacists')
def pharmacists():
    pharms = Pharmacist.query.filter_by(hospital_id=current_user.hospital_id).all()
    return render_template('admin/pharmacists.html', pharmacists=pharms)

@admin_bp.route('/pharmacists/add', methods=['GET', 'POST'])
def add_pharmacist():
    form = PharmacistForm()
    if form.validate_on_submit():
        user = User(email=form.email.data, role='Pharmacist', hospital_id=current_user.hospital_id)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()
        
        pharm = Pharmacist(
            user_id=user.id,
            hospital_id=current_user.hospital_id,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data
        )
        db.session.add(pharm)
        db.session.commit()
        
        AuditService.log_action(current_user.id, f"Added Pharmacist '{pharm.full_name}'", request.remote_addr, current_user.hospital_id)
        flash('Pharmacist registered successfully!', 'success')
        return redirect(url_for('admin.pharmacists'))
        
    return render_template('admin/pharmacist_form.html', form=form, title="Add Pharmacist")

@admin_bp.route('/pharmacists/edit/<int:id>', methods=['GET', 'POST'])
def edit_pharmacist(id):
    pharm = Pharmacist.query.filter_by(id=id, hospital_id=current_user.hospital_id).first_or_404()
    user = User.query.get(pharm.user_id)
    
    form = PharmacistForm(pharmacist_id=pharm.id)
    if form.validate_on_submit():
        user.email = form.email.data
        if form.password.data:
            user.set_password(form.password.data)
        pharm.first_name = form.first_name.data
        pharm.last_name = form.last_name.data
        pharm.phone = form.phone.data
        db.session.commit()
        
        AuditService.log_action(current_user.id, f"Updated Pharmacist '{pharm.full_name}'", request.remote_addr, current_user.hospital_id)
        flash('Pharmacist details updated successfully!', 'success')
        return redirect(url_for('admin.pharmacists'))
        
    if request.method == 'GET':
        form.first_name.data = pharm.first_name
        form.last_name.data = pharm.last_name
        form.email.data = user.email
        form.phone.data = pharm.phone
        
    return render_template('admin/pharmacist_form.html', form=form, title="Edit Pharmacist")

@admin_bp.route('/pharmacists/delete/<int:id>', methods=['POST'])
def delete_pharmacist(id):
    pharm = Pharmacist.query.filter_by(id=id, hospital_id=current_user.hospital_id).first_or_404()
    user = User.query.get(pharm.user_id)
    db.session.delete(user)
    db.session.commit()
    flash('Pharmacist profile deleted successfully.', 'success')
    return redirect(url_for('admin.pharmacists'))

# -- BILLING EXECUTIVES --
@admin_bp.route('/billing-executives')
def billing_executives():
    execs = BillingExecutive.query.filter_by(hospital_id=current_user.hospital_id).all()
    return render_template('admin/billing_executives.html', billing_executives=execs)

@admin_bp.route('/billing-executives/add', methods=['GET', 'POST'])
def add_billing_executive():
    form = BillingExecutiveForm()
    if form.validate_on_submit():
        user = User(email=form.email.data, role='BillingExecutive', hospital_id=current_user.hospital_id)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()
        
        exec_profile = BillingExecutive(
            user_id=user.id,
            hospital_id=current_user.hospital_id,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data
        )
        db.session.add(exec_profile)
        db.session.commit()
        
        AuditService.log_action(current_user.id, f"Added Billing Executive '{exec_profile.full_name}'", request.remote_addr, current_user.hospital_id)
        flash('Billing Executive registered successfully!', 'success')
        return redirect(url_for('admin.billing_executives'))
        
    return render_template('admin/billing_executive_form.html', form=form, title="Add Billing Executive")

@admin_bp.route('/billing-executives/edit/<int:id>', methods=['GET', 'POST'])
def edit_billing_executive(id):
    exec_profile = BillingExecutive.query.filter_by(id=id, hospital_id=current_user.hospital_id).first_or_404()
    user = User.query.get(exec_profile.user_id)
    
    form = BillingExecutiveForm(executive_id=exec_profile.id)
    if form.validate_on_submit():
        user.email = form.email.data
        if form.password.data:
            user.set_password(form.password.data)
        exec_profile.first_name = form.first_name.data
        exec_profile.last_name = form.last_name.data
        exec_profile.phone = form.phone.data
        db.session.commit()
        
        AuditService.log_action(current_user.id, f"Updated Billing Executive '{exec_profile.full_name}'", request.remote_addr, current_user.hospital_id)
        flash('Billing Executive details updated successfully!', 'success')
        return redirect(url_for('admin.billing_executives'))
        
    if request.method == 'GET':
        form.first_name.data = exec_profile.first_name
        form.last_name.data = exec_profile.last_name
        form.email.data = user.email
        form.phone.data = exec_profile.phone
        
    return render_template('admin/billing_executive_form.html', form=form, title="Edit Billing Executive")

@admin_bp.route('/billing-executives/delete/<int:id>', methods=['POST'])
def delete_billing_executive(id):
    exec_profile = BillingExecutive.query.filter_by(id=id, hospital_id=current_user.hospital_id).first_or_404()
    user = User.query.get(exec_profile.user_id)
    db.session.delete(user)
    db.session.commit()
    flash('Billing Executive profile deleted successfully.', 'success')
    return redirect(url_for('admin.billing_executives'))

# ----------------------------------------------------
# DEPARTMENTS
# ----------------------------------------------------

@admin_bp.route('/departments')
def departments():
    depts = Department.query.filter_by(hospital_id=current_user.hospital_id).all()
    return render_template('admin/departments.html', departments=depts)

@admin_bp.route('/departments/add', methods=['GET', 'POST'])
def add_department():
    form = DepartmentForm()
    if form.validate_on_submit():
        dept = Department(
            hospital_id=current_user.hospital_id,
            name=form.name.data,
            description=form.description.data,
            icon_name=form.icon_name.data
        )
        db.session.add(dept)
        db.session.commit()
        AuditService.log_action(current_user.id, f"Added Department '{dept.name}'", request.remote_addr, current_user.hospital_id)
        flash('Department added successfully!', 'success')
        return redirect(url_for('admin.departments'))
    return render_template('admin/department_form.html', form=form, title="Add Department")

@admin_bp.route('/departments/edit/<int:id>', methods=['GET', 'POST'])
def edit_department(id):
    dept = Department.query.filter_by(id=id, hospital_id=current_user.hospital_id).first_or_404()
    form = DepartmentForm()
    if form.validate_on_submit():
        dept.name = form.name.data
        dept.description = form.description.data
        dept.icon_name = form.icon_name.data
        db.session.commit()
        AuditService.log_action(current_user.id, f"Updated Department '{dept.name}'", request.remote_addr, current_user.hospital_id)
        flash('Department updated successfully!', 'success')
        return redirect(url_for('admin.departments'))
        
    if request.method == 'GET':
        form.name.data = dept.name
        form.description.data = dept.description
        form.icon_name.data = dept.icon_name
    return render_template('admin/department_form.html', form=form, title="Edit Department")

@admin_bp.route('/departments/delete/<int:id>', methods=['POST'])
def delete_department(id):
    dept = Department.query.filter_by(id=id, hospital_id=current_user.hospital_id).first_or_404()
    db.session.delete(dept)
    db.session.commit()
    flash('Department deleted successfully.', 'success')
    return redirect(url_for('admin.departments'))

# ----------------------------------------------------
# ROOMS
# ----------------------------------------------------

@admin_bp.route('/rooms')
def rooms():
    rooms_list = Room.query.filter_by(hospital_id=current_user.hospital_id).all()
    return render_template('admin/rooms.html', rooms=rooms_list)

@admin_bp.route('/rooms/add', methods=['GET', 'POST'])
def add_room():
    form = RoomForm()
    if form.validate_on_submit():
        room = Room(
            hospital_id=current_user.hospital_id,
            room_number=form.room_number.data,
            room_type=form.room_type.data,
            rate_per_day=form.rate_per_day.data,
            status=form.status.data
        )
        db.session.add(room)
        db.session.commit()
        AuditService.log_action(current_user.id, f"Added Room '{room.room_number}'", request.remote_addr, current_user.hospital_id)
        flash('Room added successfully!', 'success')
        return redirect(url_for('admin.rooms'))
    return render_template('admin/room_form.html', form=form, title="Add Room")

@admin_bp.route('/rooms/edit/<int:id>', methods=['GET', 'POST'])
def edit_room(id):
    room = Room.query.filter_by(id=id, hospital_id=current_user.hospital_id).first_or_404()
    form = RoomForm()
    if form.validate_on_submit():
        room.room_number = form.room_number.data
        room.room_type = form.room_type.data
        room.rate_per_day = form.rate_per_day.data
        room.status = form.status.data
        db.session.commit()
        AuditService.log_action(current_user.id, f"Updated Room '{room.room_number}'", request.remote_addr, current_user.hospital_id)
        flash('Room updated successfully!', 'success')
        return redirect(url_for('admin.rooms'))
        
    if request.method == 'GET':
        form.room_number.data = room.room_number
        form.room_type.data = room.room_type
        form.rate_per_day.data = room.rate_per_day
        form.status.data = room.status
    return render_template('admin/room_form.html', form=form, title="Edit Room")

@admin_bp.route('/rooms/delete/<int:id>', methods=['POST'])
def delete_room(id):
    room = Room.query.filter_by(id=id, hospital_id=current_user.hospital_id).first_or_404()
    db.session.delete(room)
    db.session.commit()
    flash('Room deleted successfully.', 'success')
    return redirect(url_for('admin.rooms'))

# ----------------------------------------------------
# REPORT EXPORTS & OTHER DEFAULTS
# ----------------------------------------------------

@admin_bp.route('/reports/export/<string:report_type>/<string:format_type>')
def export_reports(report_type, format_type):
    h_id = current_user.hospital_id
    
    if report_type == 'patients':
        items = Patient.query.join(Appointment).filter(Appointment.hospital_id == h_id).distinct().all()
        data = {
            'Patient ID': [p.id for p in items],
            'First Name': [p.first_name for p in items],
            'Last Name': [p.last_name for p in items],
            'Email': [p.user.email for p in items],
            'Phone': [p.phone for p in items],
            'Gender': [p.gender for p in items],
            'Date of Birth': [p.date_of_birth.strftime('%Y-%m-%d') for p in items]
        }
        filename = f"patients_report_{datetime.now().strftime('%Y%m%d')}"
        sheet_name = "Patients"
        
    elif report_type == 'appointments':
        items = Appointment.query.filter_by(hospital_id=h_id).all()
        data = {
            'Appointment ID': [a.id for a in items],
            'Patient': [a.patient.full_name for a in items],
            'Doctor': [a.doctor.full_name for a in items],
            'Department': [a.doctor.department.name for a in items],
            'Date': [a.appointment_date.strftime('%Y-%m-%d') for a in items],
            'Time Slot': [a.time_slot for a in items],
            'Status': [a.status for a in items]
        }
        filename = f"appointments_report_{datetime.now().strftime('%Y%m%d')}"
        sheet_name = "Appointments"
        
    elif report_type == 'revenue':
        items = Bill.query.filter_by(hospital_id=h_id, status='Paid').all()
        data = {
            'Bill ID': [b.id for b in items],
            'Patient': [b.patient.full_name for b in items],
            'Consultation Fee': [float(b.consultation_fee) for b in items],
            'Medicine Charges': [float(b.medicine_charges) for b in items],
            'Lab Charges': [float(b.lab_charges) for b in items],
            'Other Charges': [float(b.other_charges) for b in items],
            'GST': [float(b.gst) for b in items],
            'Discount': [float(b.discount) for b in items],
            'Grand Total': [float(b.grand_total) for b in items]
        }
        filename = f"revenue_report_{datetime.now().strftime('%Y%m%d')}"
        sheet_name = "Revenue"
        
    elif report_type == 'doctors':
        items = Doctor.query.filter_by(hospital_id=h_id).all()
        data = {
            'Doctor ID': [d.id for d in items],
            'Name': [d.full_name for d in items],
            'Department': [d.department.name for d in items],
            'Specialization': [d.specialization for d in items],
            'Phone': [d.phone for d in items],
            'Fee': [float(d.consultation_fee) for d in items]
        }
        filename = f"doctors_report_{datetime.now().strftime('%Y%m%d')}"
        sheet_name = "Doctors"
    else:
        flash("Invalid report type.", "danger")
        return redirect(url_for('admin.dashboard'))
        
    if format_type == 'excel':
        import io
        excel_data = ReportService.export_excel(data, sheet_name)
        return send_file(
            io.BytesIO(excel_data),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f"{filename}.xlsx"
        )
    elif format_type == 'csv':
        import io
        csv_data = ReportService.export_csv(data)
        return send_file(
            io.BytesIO(csv_data),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f"{filename}.csv"
        )
    else:
        flash("Unsupported export format.", "danger")
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/audit-logs')
def audit_logs():
    page = request.args.get('page', 1, type=int)
    pagination = AuditLog.query.filter_by(hospital_id=current_user.hospital_id).order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('admin/audit_logs.html', pagination=pagination)

# ----------------------------------------------------
# BILLING RECORDS
# ----------------------------------------------------

@admin_bp.route('/billing')
def billing():
    h_id = current_user.hospital_id
    page = request.args.get('page', 1, type=int)
    pagination = Bill.query.filter_by(hospital_id=h_id).order_by(Bill.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('admin/billing.html', pagination=pagination)

# ----------------------------------------------------
# PATIENTS LIST
# ----------------------------------------------------

@admin_bp.route('/patients')
def patients():
    h_id = current_user.hospital_id
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    query = Patient.query.join(Appointment).filter(Appointment.hospital_id == h_id).distinct()
    if search:
        query = query.filter(
            (Patient.first_name.ilike(f'%{search}%')) |
            (Patient.last_name.ilike(f'%{search}%'))
        )
    pagination = query.order_by(Patient.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('admin/patients.html', pagination=pagination, search=search)

# ----------------------------------------------------
# LAB TESTS
# ----------------------------------------------------

@admin_bp.route('/lab-tests')
def lab_tests():
    h_id = current_user.hospital_id
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '')
    category_filter = request.args.get('category', '')

    query = LabTest.query.filter_by(hospital_id=h_id)
    if search:
        query = query.join(Patient).filter(
            (Patient.first_name.ilike(f'%{search}%')) |
            (Patient.last_name.ilike(f'%{search}%'))
        )
    if status_filter:
        query = query.filter(LabTest.status == status_filter)
    if category_filter:
        query = query.filter(LabTest.test_category == category_filter)

    pagination = query.order_by(LabTest.test_date.desc()).paginate(page=page, per_page=15)

    stats = {
        'total': LabTest.query.filter_by(hospital_id=h_id).count(),
        'pending': LabTest.query.filter_by(hospital_id=h_id).filter(~LabTest.status.in_(['Completed', 'Delivered', 'Cancelled'])).count(),
        'completed': LabTest.query.filter_by(hospital_id=h_id).filter(LabTest.status.in_(['Completed', 'Delivered'])).count(),
        'revenue': float(db.session.query(func.sum(LabTest.cost)).filter(LabTest.hospital_id == h_id, LabTest.status.in_(['Completed', 'Delivered'])).scalar() or 0)
    }

    return render_template(
        'admin/lab_tests.html',
        pagination=pagination,
        stats=stats,
        search=search,
        status_filter=status_filter,
        category_filter=category_filter
    )

# ----------------------------------------------------
# LAB TEST TEMPLATES CRUD
# ----------------------------------------------------

@admin_bp.route('/lab-templates')
def lab_templates():
    templates = LabTestTemplate.query.filter_by(hospital_id=current_user.hospital_id).order_by(LabTestTemplate.test_category, LabTestTemplate.test_name).all()
    return render_template('admin/lab_templates.html', templates=templates)

@admin_bp.route('/lab-templates/add', methods=['GET', 'POST'])
def add_lab_template():
    form = LabTestTemplateForm()
    if form.validate_on_submit():
        template = LabTestTemplate(
            hospital_id=current_user.hospital_id,
            test_name=form.test_name.data.strip(),
            test_category=form.test_category.data,
            normal_range_min=form.normal_range_min.data,
            normal_range_max=form.normal_range_max.data,
            normal_range_text=form.normal_range_text.data.strip() if form.normal_range_text.data else None,
            unit=form.unit.data.strip() if form.unit.data else None,
            age_min=form.age_min.data if form.age_min.data is not None else 0,
            age_max=form.age_max.data if form.age_max.data is not None else 120,
            gender=form.gender.data,
            critical_range_min=form.critical_range_min.data,
            critical_range_max=form.critical_range_max.data,
            cost=form.cost.data
        )
        db.session.add(template)
        db.session.commit()
        AuditService.log_action(current_user.id, f"Created Lab Test Template: {template.test_name}", request.remote_addr)
        flash(f"Test template '{template.test_name}' added successfully!", 'success')
        return redirect(url_for('admin.lab_templates'))
    return render_template('admin/lab_template_form.html', form=form, title="Add Lab Test Parameter")

@admin_bp.route('/lab-templates/edit/<int:id>', methods=['GET', 'POST'])
def edit_lab_template(id):
    template = LabTestTemplate.query.get_or_404(id)
    form = LabTestTemplateForm(obj=template)
    if form.validate_on_submit():
        template.test_name = form.test_name.data.strip()
        template.test_category = form.test_category.data
        template.normal_range_min = form.normal_range_min.data
        template.normal_range_max = form.normal_range_max.data
        template.normal_range_text = form.normal_range_text.data.strip() if form.normal_range_text.data else None
        template.unit = form.unit.data.strip() if form.unit.data else None
        template.age_min = form.age_min.data if form.age_min.data is not None else 0
        template.age_max = form.age_max.data if form.age_max.data is not None else 120
        template.gender = form.gender.data
        template.critical_range_min = form.critical_range_min.data
        template.critical_range_max = form.critical_range_max.data
        template.cost = form.cost.data
        db.session.commit()
        AuditService.log_action(current_user.id, f"Edited Lab Test Template ID: {template.id}", request.remote_addr)
        flash(f"Test template '{template.test_name}' updated successfully!", 'success')
        return redirect(url_for('admin.lab_templates'))
    return render_template('admin/lab_template_form.html', form=form, title="Edit Lab Test Parameter")

@admin_bp.route('/lab-templates/delete/<int:id>', methods=['POST'])
def delete_lab_template(id):
    template = LabTestTemplate.query.get_or_404(id)
    db.session.delete(template)
    db.session.commit()
    AuditService.log_action(current_user.id, f"Deleted Lab Test Template ID: {id}", request.remote_addr)
    flash("Test template deleted successfully!", 'success')
    return redirect(url_for('admin.lab_templates'))

# ----------------------------------------------------
# LAB PACKAGES CRUD
# ----------------------------------------------------

@admin_bp.route('/lab-packages')
def lab_packages():
    packages = LabPackage.query.filter_by(hospital_id=current_user.hospital_id).order_by(LabPackage.name).all()
    return render_template('admin/lab_packages.html', packages=packages)

@admin_bp.route('/lab-packages/add', methods=['GET', 'POST'])
def add_lab_package():
    form = LabPackageForm()
    templates_list = LabTestTemplate.query.filter_by(hospital_id=current_user.hospital_id).order_by(LabTestTemplate.test_name).all()
    form.templates.choices = [(t.id, f"{t.test_name} ({t.test_category})") for t in templates_list]

    if form.validate_on_submit():
        package = LabPackage(
            hospital_id=current_user.hospital_id,
            name=form.name.data.strip(),
            description=form.description.data.strip() if form.description.data else None,
            cost=form.cost.data
        )
        selected_template_ids = form.templates.data
        selected_templates = LabTestTemplate.query.filter(LabTestTemplate.id.in_(selected_template_ids)).all()
        package.templates = selected_templates

        db.session.add(package)
        db.session.commit()

        AuditService.log_action(current_user.id, f"Created Lab Package: {package.name}", request.remote_addr)
        flash(f"Lab Package '{package.name}' added successfully!", 'success')
        return redirect(url_for('admin.lab_packages'))

    return render_template('admin/lab_package_form.html', form=form, title="Add Laboratory Package")

@admin_bp.route('/lab-packages/edit/<int:id>', methods=['GET', 'POST'])
def edit_lab_package(id):
    package = LabPackage.query.get_or_404(id)
    form = LabPackageForm(obj=package)

    templates_list = LabTestTemplate.query.filter_by(hospital_id=current_user.hospital_id).order_by(LabTestTemplate.test_name).all()
    form.templates.choices = [(t.id, f"{t.test_name} ({t.test_category})") for t in templates_list]

    if request.method == 'GET':
        form.templates.data = [t.id for t in package.templates]

    if form.validate_on_submit():
        package.name = form.name.data.strip()
        package.description = form.description.data.strip() if form.description.data else None
        package.cost = form.cost.data

        selected_template_ids = form.templates.data
        selected_templates = LabTestTemplate.query.filter(LabTestTemplate.id.in_(selected_template_ids)).all()
        package.templates = selected_templates

        db.session.commit()

        AuditService.log_action(current_user.id, f"Updated Lab Package ID: {package.id}", request.remote_addr)
        flash(f"Lab Package '{package.name}' updated successfully!", 'success')
        return redirect(url_for('admin.lab_packages'))

    return render_template('admin/lab_package_form.html', form=form, title="Edit Laboratory Package")

@admin_bp.route('/lab-packages/delete/<int:id>', methods=['POST'])
def delete_lab_package(id):
    package = LabPackage.query.get_or_404(id)
    db.session.delete(package)
    db.session.commit()
    AuditService.log_action(current_user.id, f"Deleted Lab Package ID: {id}", request.remote_addr)
    flash("Lab package deleted successfully!", 'success')
    return redirect(url_for('admin.lab_packages'))

# ----------------------------------------------------
# REPORTS
# ----------------------------------------------------

@admin_bp.route('/reports')
def reports():
    return render_template('admin/reports.html')

# ----------------------------------------------------
# APPOINTMENTS
# ----------------------------------------------------

@admin_bp.route('/appointments')
def appointments():
    h_id = current_user.hospital_id
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    query = Appointment.query.filter_by(hospital_id=h_id)
    if search:
        query = query.join(Patient).filter(
            (Patient.first_name.ilike(f'%{search}%')) |
            (Patient.last_name.ilike(f'%{search}%'))
        )
    pagination = query.order_by(Appointment.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('admin/appointments.html', pagination=pagination, search=search)

@admin_bp.route('/appointments/<int:id>/cancel', methods=['POST'])
def cancel_appointment(id):
    appt = Appointment.query.get_or_404(id)
    if appt.hospital_id != current_user.hospital_id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('admin.appointments'))
    appt.status = 'Cancelled'
    db.session.commit()
    AuditService.log_action(current_user.id, f"Cancelled Appointment ID: {id}", request.remote_addr)
    flash('Appointment cancelled successfully.', 'success')
    return redirect(url_for('admin.appointments'))

# ----------------------------------------------------
# DELETE PATIENT
# ----------------------------------------------------

@admin_bp.route('/patients/delete/<int:id>', methods=['POST'])
def delete_patient(id):
    patient = Patient.query.get_or_404(id)
    user = User.query.get(patient.user_id)
    db.session.delete(patient)
    if user:
        db.session.delete(user)
    db.session.commit()
    AuditService.log_action(current_user.id, f"Deleted Patient ID: {id}", request.remote_addr)
    flash('Patient record deleted successfully.', 'success')
    return redirect(url_for('admin.patients'))

# ----------------------------------------------------
# GLOBAL SEARCH
# ----------------------------------------------------

@admin_bp.route('/search')
def global_search():
    h_id = current_user.hospital_id
    q = request.args.get('q', '').strip()
    results = {
        'doctors': [],
        'patients': [],
        'appointments': []
    }
    if q:
        results['doctors'] = Doctor.query.filter_by(hospital_id=h_id).filter(
            (Doctor.first_name.ilike(f'%{q}%')) | (Doctor.last_name.ilike(f'%{q}%'))
        ).limit(10).all()
        results['patients'] = Patient.query.join(Appointment).filter(
            Appointment.hospital_id == h_id,
            (Patient.first_name.ilike(f'%{q}%')) | (Patient.last_name.ilike(f'%{q}%'))
        ).distinct().limit(10).all()
        results['appointments'] = Appointment.query.filter_by(hospital_id=h_id).join(Patient).filter(
            (Patient.first_name.ilike(f'%{q}%')) | (Patient.last_name.ilike(f'%{q}%'))
        ).limit(10).all()
    return render_template('admin/search_results.html', results=results, query=q)


