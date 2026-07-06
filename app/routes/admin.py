from datetime import datetime, date
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, Response, g
from flask_login import login_required, current_user
from sqlalchemy import func

from app.models import db
from app.models.user import User, Doctor, Patient, Receptionist
from app.models.department import Department
from app.models.appointment import Appointment
from app.models.billing import Bill, Payment
from app.models.room import Room
from app.models.audit_log import AuditLog
from app.models.lab_test import LabTest
from app.forms import DoctorForm, ReceptionistForm, DepartmentForm, RoomForm
from app.services import AuditService, ReportService

admin_bp = Blueprint('admin', __name__)

# Middleware to ensure only Admins can access this blueprint
@admin_bp.before_request
@login_required
def admin_required():
    if current_user.role != 'Admin':
        flash('Unauthorized access! You do not have permission to view this page.', 'danger')
        return redirect(url_for('auth.login'))

@admin_bp.route('/dashboard')
def dashboard():
    # 1. Card Statistics
    total_patients = Patient.query.count()
    total_doctors = Doctor.query.count()
    total_receptionists = Receptionist.query.count()
    
    today_str = date.today()
    today_appointments = Appointment.query.filter_by(appointment_date=today_str).count()
    
    # Available Doctors
    available_docs_count = Doctor.query.filter_by(availability_status='Available').count()
    
    # Monthly Revenue calculation
    current_month = datetime.now().month
    current_year = datetime.now().year
    monthly_revenue_q = db.session.query(func.sum(Bill.grand_total)).filter(
        func.extract('month', Bill.created_at) == current_month,
        func.extract('year', Bill.created_at) == current_year,
        Bill.status == 'Paid'
    ).scalar()
    monthly_revenue = monthly_revenue_q or 0.00

    # 2. Charts Data Queries
    # - Appointments per month (last 6 months)
    # - Revenue per month (last 6 months)
    # - Patient growth (registered per month)
    # - Doctor performance (completed appointments per doctor)
    
    # Recent activity / appointments
    recent_appointments = Appointment.query.order_by(Appointment.created_at.desc()).limit(5).all()
    recent_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(5).all()

    return render_template(
        'admin/dashboard.html',
        total_patients=total_patients,
        total_doctors=total_doctors,
        total_receptionists=total_receptionists,
        today_appointments=today_appointments,
        available_docs_count=available_docs_count,
        monthly_revenue=monthly_revenue,
        recent_appointments=recent_appointments,
        recent_logs=recent_logs
    )

# --- DOCTOR CRUD ---
@admin_bp.route('/doctors')
def doctors():
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    
    query = Doctor.query
    if search:
        query = query.filter(
            (Doctor.first_name.like(f"%{search}%")) | 
            (Doctor.last_name.like(f"%{search}%")) |
            (Doctor.specialization.like(f"%{search}%"))
        )
        
    pagination = query.paginate(page=page, per_page=10)
    return render_template('admin/doctors.html', pagination=pagination, search=search)

@admin_bp.route('/doctors/add', methods=['GET', 'POST'])
def add_doctor():
    form = DoctorForm()
    if form.validate_on_submit():
        # First check if password is provided
        if not form.password.data:
            form.password.errors.append("Password is required for a new doctor account.")
            return render_template('admin/doctor_form.html', form=form, title="Add Doctor")
            
        user = User(email=form.email.data, role='Doctor')
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush() # Populate user.id
        
        doctor = Doctor(
            user_id=user.id,
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
        
        AuditService.log_action(current_user.id, f"Added Doctor: {doctor.full_name}")
        flash(f"Doctor {doctor.full_name} added successfully!", "success")
        return redirect(url_for('admin.doctors'))
        
    return render_template('admin/doctor_form.html', form=form, title="Add Doctor")

@admin_bp.route('/doctors/edit/<int:id>', methods=['GET', 'POST'])
def edit_doctor(id):
    doctor = Doctor.query.get_or_404(id)
    form = DoctorForm(doctor_id=id)
    
    if form.validate_on_submit():
        doctor.user.email = form.email.data
        doctor.first_name = form.first_name.data
        doctor.last_name = form.last_name.data
        doctor.phone = form.phone.data
        doctor.department_id = form.department_id.data
        doctor.specialization = form.specialization.data
        doctor.qualification = form.qualification.data
        doctor.consultation_fee = form.consultation_fee.data
        doctor.bio = form.bio.data
        doctor.availability_status = form.availability_status.data
        
        if form.password.data:
            doctor.user.set_password(form.password.data)
            
        db.session.commit()
        AuditService.log_action(current_user.id, f"Edited Doctor: {doctor.full_name}")
        flash(f"Doctor {doctor.full_name} details updated successfully!", "success")
        return redirect(url_for('admin.doctors'))
        
    elif request.method == 'GET':
        form.email.data = doctor.user.email
        form.first_name.data = doctor.first_name
        form.last_name.data = doctor.last_name
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
    doctor = Doctor.query.get_or_404(id)
    user = doctor.user
    full_name = doctor.full_name
    db.session.delete(user) # Cascades to doctor
    db.session.commit()
    AuditService.log_action(current_user.id, f"Deleted Doctor Account: {full_name}")
    flash(f"Doctor {full_name} deleted successfully.", "success")
    return redirect(url_for('admin.doctors'))

# --- RECEPTIONIST CRUD ---
@admin_bp.route('/receptionists')
def receptionists():
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    
    query = Receptionist.query
    if search:
        query = query.filter(
            (Receptionist.first_name.like(f"%{search}%")) |
            (Receptionist.last_name.like(f"%{search}%"))
        )
    pagination = query.paginate(page=page, per_page=10)
    return render_template('admin/receptionists.html', pagination=pagination, search=search)

@admin_bp.route('/receptionists/add', methods=['GET', 'POST'])
def add_receptionist():
    form = ReceptionistForm()
    if form.validate_on_submit():
        if not form.password.data:
            form.password.errors.append("Password is required for a new receptionist account.")
            return render_template('admin/receptionist_form.html', form=form, title="Add Receptionist")
            
        user = User(email=form.email.data, role='Receptionist')
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()
        
        receptionist = Receptionist(
            user_id=user.id,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data,
            shift=form.shift.data
        )
        db.session.add(receptionist)
        db.session.commit()
        
        AuditService.log_action(current_user.id, f"Added Receptionist: {receptionist.full_name}")
        flash(f"Receptionist {receptionist.full_name} added successfully!", "success")
        return redirect(url_for('admin.receptionists'))
        
    return render_template('admin/receptionist_form.html', form=form, title="Add Receptionist")

@admin_bp.route('/receptionists/edit/<int:id>', methods=['GET', 'POST'])
def edit_receptionist(id):
    receptionist = Receptionist.query.get_or_404(id)
    form = ReceptionistForm(receptionist_id=id)
    
    if form.validate_on_submit():
        receptionist.user.email = form.email.data
        receptionist.first_name = form.first_name.data
        receptionist.last_name = form.last_name.data
        receptionist.phone = form.phone.data
        receptionist.shift = form.shift.data
        
        if form.password.data:
            receptionist.user.set_password(form.password.data)
            
        db.session.commit()
        AuditService.log_action(current_user.id, f"Edited Receptionist: {receptionist.full_name}")
        flash(f"Receptionist {receptionist.full_name} details updated successfully!", "success")
        return redirect(url_for('admin.receptionists'))
        
    elif request.method == 'GET':
        form.email.data = receptionist.user.email
        form.first_name.data = receptionist.first_name
        form.last_name.data = receptionist.last_name
        form.phone.data = receptionist.phone
        form.shift.data = receptionist.shift
        
    return render_template('admin/receptionist_form.html', form=form, title="Edit Receptionist")

@admin_bp.route('/receptionists/delete/<int:id>', methods=['POST'])
def delete_receptionist(id):
    receptionist = Receptionist.query.get_or_404(id)
    user = receptionist.user
    full_name = receptionist.full_name
    db.session.delete(user) # Cascades
    db.session.commit()
    AuditService.log_action(current_user.id, f"Deleted Receptionist Account: {full_name}")
    flash(f"Receptionist {full_name} deleted successfully.", "success")
    return redirect(url_for('admin.receptionists'))

# --- PATIENT MANAGEMENT ---
@admin_bp.route('/patients')
def patients():
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    
    query = Patient.query
    if search:
        query = query.filter(
            (Patient.first_name.like(f"%{search}%")) |
            (Patient.last_name.like(f"%{search}%")) |
            (Patient.phone.like(f"%{search}%"))
        )
    pagination = query.paginate(page=page, per_page=10)
    return render_template('admin/patients.html', pagination=pagination, search=search)

@admin_bp.route('/patients/delete/<int:id>', methods=['POST'])
def delete_patient(id):
    patient = Patient.query.get_or_404(id)
    user = patient.user
    full_name = patient.full_name
    db.session.delete(user) # Cascades
    db.session.commit()
    AuditService.log_action(current_user.id, f"Deleted Patient Account: {full_name}")
    flash(f"Patient {full_name} account deleted successfully.", "success")
    return redirect(url_for('admin.patients'))

# --- DEPARTMENTS ---
@admin_bp.route('/departments')
def departments():
    depts = Department.query.order_by(Department.name).all()
    return render_template('admin/departments.html', departments=depts)

@admin_bp.route('/departments/add', methods=['GET', 'POST'])
def add_department():
    form = DepartmentForm()
    if form.validate_on_submit():
        dept = Department(
            name=form.name.data,
            description=form.description.data,
            icon_name=form.icon_name.data
        )
        db.session.add(dept)
        db.session.commit()
        AuditService.log_action(current_user.id, f"Added Department: {dept.name}")
        flash(f"Department {dept.name} added successfully!", "success")
        return redirect(url_for('admin.departments'))
    return render_template('admin/department_form.html', form=form, title="Add Department")

@admin_bp.route('/departments/edit/<int:id>', methods=['GET', 'POST'])
def edit_department(id):
    dept = Department.query.get_or_404(id)
    form = DepartmentForm(dept_id=id)
    
    if form.validate_on_submit():
        dept.name = form.name.data
        dept.description = form.description.data
        dept.icon_name = form.icon_name.data
        db.session.commit()
        AuditService.log_action(current_user.id, f"Edited Department: {dept.name}")
        flash(f"Department {dept.name} updated successfully!", "success")
        return redirect(url_for('admin.departments'))
        
    elif request.method == 'GET':
        form.name.data = dept.name
        form.description.data = dept.description
        form.icon_name.data = dept.icon_name
        
    return render_template('admin/department_form.html', form=form, title="Edit Department")

@admin_bp.route('/departments/delete/<int:id>', methods=['POST'])
def delete_department(id):
    dept = Department.query.get_or_404(id)
    name = dept.name
    try:
        db.session.delete(dept)
        db.session.commit()
        AuditService.log_action(current_user.id, f"Deleted Department: {name}")
        flash(f"Department {name} deleted successfully.", "success")
    except Exception:
        db.session.rollback()
        flash(f"Cannot delete department {name} because it is assigned to doctors.", "danger")
    return redirect(url_for('admin.departments'))

# --- ROOMS ---
@admin_bp.route('/rooms')
def rooms():
    rooms_list = Room.query.order_by(Room.room_number).all()
    return render_template('admin/rooms.html', rooms=rooms_list)

@admin_bp.route('/rooms/add', methods=['GET', 'POST'])
def add_room():
    form = RoomForm()
    if form.validate_on_submit():
        room = Room(
            room_number=form.room_number.data,
            room_type=form.room_type.data,
            status=form.status.data,
            rate_per_day=form.rate_per_day.data
        )
        db.session.add(room)
        db.session.commit()
        AuditService.log_action(current_user.id, f"Added Room: {room.room_number}")
        flash(f"Room {room.room_number} added successfully!", "success")
        return redirect(url_for('admin.rooms'))
    return render_template('admin/room_form.html', form=form, title="Add Room")

@admin_bp.route('/rooms/edit/<int:id>', methods=['GET', 'POST'])
def edit_room(id):
    room = Room.query.get_or_404(id)
    form = RoomForm(room_id=id)
    
    if form.validate_on_submit():
        room.room_number = form.room_number.data
        room.room_type = form.room_type.data
        room.status = form.status.data
        room.rate_per_day = form.rate_per_day.data
        db.session.commit()
        AuditService.log_action(current_user.id, f"Edited Room: {room.room_number}")
        flash(f"Room {room.room_number} details updated successfully!", "success")
        return redirect(url_for('admin.rooms'))
        
    elif request.method == 'GET':
        form.room_number.data = room.room_number
        form.room_type.data = room.room_type
        form.status.data = room.status
        form.rate_per_day.data = room.rate_per_day
        
    return render_template('admin/room_form.html', form=form, title="Edit Room")

@admin_bp.route('/rooms/delete/<int:id>', methods=['POST'])
def delete_room(id):
    room = Room.query.get_or_404(id)
    num = room.room_number
    db.session.delete(room)
    db.session.commit()
    AuditService.log_action(current_user.id, f"Deleted Room: {num}")
    flash(f"Room {num} deleted successfully.", "success")
    return redirect(url_for('admin.rooms'))

# --- APPOINTMENT MANAGEMENT ---
@admin_bp.route('/appointments')
def appointments():
    page = request.args.get('page', 1, type=int)
    pagination = Appointment.query.order_by(Appointment.appointment_date.desc()).paginate(page=page, per_page=15)
    return render_template('admin/appointments.html', pagination=pagination)

@admin_bp.route('/appointments/cancel/<int:id>', methods=['POST'])
def cancel_appointment(id):
    appt = Appointment.query.get_or_404(id)
    appt.status = 'Cancelled'
    db.session.commit()
    
    AuditService.log_action(current_user.id, f"Cancelled Appointment #{appt.id}")
    
    # Notify Patient and Doctor
    from app.services.notification_service import NotificationService
    NotificationService.create_notification(
        appt.patient.user_id,
        "Appointment Cancelled by Admin",
        f"Your appointment with {appt.doctor.full_name} on {appt.appointment_date} has been cancelled."
    )
    NotificationService.create_notification(
        appt.doctor.user_id,
        "Appointment Cancelled by Admin",
        f"The appointment of patient {appt.patient.full_name} on {appt.appointment_date} has been cancelled."
    )
    
    flash(f"Appointment #{id} cancelled successfully.", "warning")
    return redirect(url_for('admin.appointments'))

# --- BILLS MANAGEMENT ---
@admin_bp.route('/billing')
def billing():
    page = request.args.get('page', 1, type=int)
    pagination = Bill.query.order_by(Bill.created_at.desc()).paginate(page=page, per_page=15)
    return render_template('admin/billing.html', pagination=pagination)

# --- REPORTS & EXPORT ---
@admin_bp.route('/reports')
def reports():
    return render_template('admin/reports.html')

@admin_bp.route('/reports/export/<string:report_type>/<string:format_type>')
def export_reports(report_type, format_type):
    # Retrieve data based on type
    if report_type == 'patients':
        items = Patient.query.all()
        data = {
            'Patient ID': [p.id for p in items],
            'First Name': [p.first_name for p in items],
            'Last Name': [p.last_name for p in items],
            'Email': [p.user.email for p in items],
            'Phone': [p.phone for p in items],
            'Gender': [p.gender for p in items],
            'Date of Birth': [p.date_of_birth.strftime('%Y-%m-%d') for p in items],
            'Blood Group': [p.blood_group for p in items]
        }
        filename = f"patients_report_{datetime.now().strftime('%Y%m%d')}"
        sheet_name = "Patients"
        
    elif report_type == 'appointments':
        items = Appointment.query.all()
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
        items = Bill.query.filter_by(status='Paid').all()
        data = {
            'Bill ID': [b.id for b in items],
            'Patient': [b.patient.full_name for b in items],
            'Consultation Fee': [float(b.consultation_fee) for b in items],
            'Medicine Charges': [float(b.medicine_charges) for b in items],
            'Lab Charges': [float(b.lab_charges) for b in items],
            'Other Charges': [float(b.other_charges) for b in items],
            'GST (18%)': [float(b.gst) for b in items],
            'Discount': [float(b.discount) for b in items],
            'Grand Total': [float(b.grand_total) for b in items],
            'Paid Date': [b.created_at.strftime('%Y-%m-%d') for b in items]
        }
        filename = f"revenue_report_{datetime.now().strftime('%Y%m%d')}"
        sheet_name = "Revenue"
        
    elif report_type == 'doctors':
        items = Doctor.query.all()
        data = {
            'Doctor ID': [d.id for d in items],
            'Name': [d.full_name for d in items],
            'Department': [d.department.name for d in items],
            'Specialization': [d.specialization for d in items],
            'Phone': [d.phone for d in items],
            'Consultation Fee': [float(d.consultation_fee) for d in items],
            'Availability': [d.availability_status for d in items],
            'Total Appointments': [len(d.appointments) for d in items]
        }
        filename = f"doctors_report_{datetime.now().strftime('%Y%m%d')}"
        sheet_name = "Doctors"
    else:
        flash("Invalid report type requested.", "danger")
        return redirect(url_for('admin.reports'))

    # Format export
    if format_type == 'excel':
        excel_data = ReportService.export_excel(data, sheet_name)
        return Response(
            excel_data,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment;filename={filename}.xlsx"}
        )
    elif format_type == 'csv':
        csv_data = ReportService.export_csv(data)
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename={filename}.csv"}
        )
        
    flash("Invalid format type requested.", "danger")
    return redirect(url_for('admin.reports'))

# --- AUDIT LOGS ---
@admin_bp.route('/audit-logs')
def audit_logs():
    page = request.args.get('page', 1, type=int)
    pagination = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('admin/audit_logs.html', pagination=pagination)

# --- GLOBAL SEARCH API/PAGE ---
@admin_bp.route('/search')
def global_search():
    q = request.args.get('q', '').strip()
    results = {
        'patients': [],
        'doctors': [],
        'appointments': [],
        'bills': []
    }
    
    if q:
        # Search Patients
        results['patients'] = Patient.query.filter(
            (Patient.first_name.like(f"%{q}%")) |
            (Patient.last_name.like(f"%{q}%")) |
            (Patient.phone.like(f"%{q}%"))
        ).limit(5).all()
        
        # Search Doctors
        results['doctors'] = Doctor.query.filter(
            (Doctor.first_name.like(f"%{q}%")) |
            (Doctor.last_name.like(f"%{q}%")) |
            (Doctor.specialization.like(f"%{q}%"))
        ).limit(5).all()
        
        # Search Appointments
        results['appointments'] = Appointment.query.join(Patient).filter(
            (Patient.first_name.like(f"%{q}%")) |
            (Patient.last_name.like(f"%{q}%"))
        ).limit(5).all()
        
        # Search Bills
        results['bills'] = Bill.query.join(Patient).filter(
            (Patient.first_name.like(f"%{q}%")) |
            (Patient.last_name.like(f"%{q}%"))
        ).limit(5).all()
        
    return render_template('admin/search_results.html', query=q, results=results)


# --- CHART DATA API (For dashboard charts rendering via Chart.js) ---
@admin_bp.route('/api/dashboard-charts')
def api_dashboard_charts():
    # 1. Appointments per month (last 6 months)
    # 2. Revenue per month (last 6 months)
    # For SQLite compatibility, we can query dates, group by month, and sort.
    # To keep it extremely robust and clean, we will query appointments from db and aggregate in python.
    appts = Appointment.query.all()
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
    appt_counts = [0] * 12
    revenue_totals = [0.00] * 12
    
    # Fill in monthly aggregates
    for a in appts:
        month_idx = a.appointment_date.month - 1
        appt_counts[month_idx] += 1
        
    bills = Bill.query.filter_by(status='Paid').all()
    for b in bills:
        month_idx = b.created_at.month - 1
        revenue_totals[month_idx] += float(b.grand_total)
        
    # Patient growth (registered count by month)
    patients = Patient.query.all()
    patient_counts = [0] * 12
    for p in patients:
        month_idx = p.created_at.month - 1
        patient_counts[month_idx] += 1
        
    # Doctor performance (number of appointments completed per doctor)
    doctors_list = Doctor.query.all()
    doc_labels = [d.full_name for d in doctors_list]
    doc_performance = [
        Appointment.query.filter_by(doctor_id=d.id, status='Completed').count() for d in doctors_list
    ]

    return {
        'months': months,
        'appointments': appt_counts,
        'revenue': revenue_totals,
        'patient_growth': patient_counts,
        'doctor_performance': {
            'labels': doc_labels,
            'data': doc_performance
        }
    }

# --- SYSTEM SETTINGS ---
@admin_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    from app.models.setting import SystemSetting
    from app.services.audit_service import AuditService
    
    hospital_name_setting = SystemSetting.query.filter_by(setting_key='hospital_name').first()
    if not hospital_name_setting:
        hospital_name_setting = SystemSetting(setting_key='hospital_name', setting_value='Hospital Portal')
        db.session.add(hospital_name_setting)
        db.session.commit()
        
    if request.method == 'POST':
        new_name = request.form.get('hospital_name', '').strip()
        if new_name:
            hospital_name_setting.setting_value = new_name
            db.session.commit()
            AuditService.log_action(current_user.id, f"Updated hospital name setting to: {new_name}", request.remote_addr)
            flash("System settings updated successfully!", "success")
            return redirect(url_for('admin.settings'))
        else:
            flash("Hospital name cannot be empty.", "danger")
            
    return render_template('admin/settings.html', hospital_name=hospital_name_setting.setting_value)

# --- LAB TESTS MANAGEMENT ---
@admin_bp.route('/lab-tests')
def lab_tests():
    search = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    category_filter = request.args.get('category', '')
    page = request.args.get('page', 1, type=int)
    
    query = LabTest.query
    
    if search:
        from app.models.user import Patient
        query = query.join(Patient).filter(
            (Patient.first_name.like(f"%{search}%")) |
            (Patient.last_name.like(f"%{search}%"))
        )
    if status_filter:
        query = query.filter(LabTest.status == status_filter)
    if category_filter:
        query = query.filter(LabTest.test_category == category_filter)
    
    pagination = query.order_by(LabTest.test_date.desc()).paginate(page=page, per_page=15)
    
    # Stats
    stats = {
        'total': LabTest.query.count(),
        'pending': LabTest.query.filter(LabTest.status != 'Completed', LabTest.status != 'Cancelled').count(),
        'completed': LabTest.query.filter_by(status='Completed').count(),
        'revenue': float(db.session.query(func.sum(LabTest.cost)).filter_by(status='Completed').scalar() or 0)
    }
    
    return render_template(
        'admin/lab_tests.html',
        pagination=pagination,
        stats=stats,
        search=search,
        status_filter=status_filter,
        category_filter=category_filter
    )
