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
    docs = Doctor.query.filter_by(hospital_id=current_user.hospital_id).all()
    return render_template('admin/doctors.html', doctors=docs)

@admin_bp.route('/doctors/add', methods=['GET', 'POST'])
def add_doctor():
    form = DoctorForm()
    # Populate departments dropdown from hospital departments
    form.department_id.choices = [(d.id, d.name) for d in Department.query.filter_by(hospital_id=current_user.hospital_id).all()]
    
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
    recs = Receptionist.query.filter_by(hospital_id=current_user.hospital_id).all()
    return render_template('admin/receptionists.html', receptionists=recs)

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
    techs = LabTechnician.query.filter_by(hospital_id=current_user.hospital_id).all()
    return render_template('admin/lab_technicians.html', lab_technicians=techs)

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
        return ReportService.export_excel(data, filename, sheet_name)
    elif format_type == 'csv':
        return ReportService.export_csv(data, filename)
    else:
        flash("Unsupported export format.", "danger")
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/audit-logs')
def audit_logs():
    logs = AuditLog.query.filter_by(hospital_id=current_user.hospital_id).order_by(AuditLog.created_at.desc()).all()
    return render_template('admin/audit_logs.html', logs=logs)
