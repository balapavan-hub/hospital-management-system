from datetime import date, datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user

from app.models import db
from app.models.user import User, Patient, Doctor
from app.models.appointment import Appointment
from app.models.billing import Bill
from app.forms import QuickRegisterPatientForm, GenerateBillForm, BookAppointmentForm
from app.services import AppointmentService, BillingService, AuditService, NotificationService, ReportService

receptionist_bp = Blueprint('receptionist', __name__)

@receptionist_bp.before_request
@login_required
def receptionist_required():
    if current_user.role != 'Receptionist':
        flash('Unauthorized access! You do not have permission to view this page.', 'danger')
        return redirect(url_for('auth.login'))

@receptionist_bp.route('/dashboard')
def dashboard():
    today = date.today()
    
    # Dashboard items
    today_appointments = Appointment.query.filter_by(appointment_date=today).order_by(Appointment.time_slot).all()
    waiting_patients = Appointment.query.filter_by(appointment_date=today, status='Pending').all()
    confirmed_appointments = Appointment.query.filter_by(appointment_date=today, status='Confirmed').all()
    
    stats = {
        'total_today': len(today_appointments),
        'waiting_count': len(waiting_patients),
        'confirmed_count': len(confirmed_appointments),
        'completed_count': Appointment.query.filter_by(appointment_date=today, status='Completed').count()
    }
    
    return render_template(
        'receptionist/dashboard.html',
        today_appointments=today_appointments,
        waiting_patients=waiting_patients,
        stats=stats
    )

@receptionist_bp.route('/register-patient', methods=['GET', 'POST'])
def register_patient():
    form = QuickRegisterPatientForm()
    if form.validate_on_submit():
        # Create User
        user = User(email=form.email.data, role='Patient')
        # Assign a default password for receptionist-created patients (e.g. welcome123)
        user.set_password('welcome123')
        db.session.add(user)
        db.session.flush()
        
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
        
        AuditService.log_action(current_user.id, f"Registered Patient (Front Desk): {patient.full_name}")
        NotificationService.create_notification(
            user.id,
            "Welcome to MediCare",
            "Your profile has been created. Your default login password is 'welcome123'. Please change it after your first login."
        )
        
        flash(f"Patient {patient.full_name} registered successfully! Default password is 'welcome123'.", 'success')
        return redirect(url_for('receptionist.dashboard'))
        
    return render_template('receptionist/register_patient.html', form=form)

@receptionist_bp.route('/book-appointment', methods=['GET', 'POST'])
def book_appointment():
    form = BookAppointmentForm()
    # List of all patients to select from in front desk booking
    patients_list = Patient.query.order_by(Patient.first_name).all()
    
    if request.method == 'POST':
        patient_id = request.form.get('patient_id', type=int)
        doc_id = form.doctor_id.data
        appt_date = form.appointment_date.data
        slot = form.time_slot.data
        
        if not patient_id or patient_id == 0:
            flash("Please select a patient.", "danger")
            return render_template('receptionist/book_appointment.html', form=form, patients=patients_list)
            
        if not AppointmentService.is_slot_available(doc_id, appt_date, slot):
            flash('The selected slot is booked. Please choose another.', 'danger')
            return render_template('receptionist/book_appointment.html', form=form, patients=patients_list)
            
        appt = Appointment(
            patient_id=patient_id,
            doctor_id=doc_id,
            appointment_date=appt_date,
            time_slot=slot,
            reason=form.reason.data,
            status='Confirmed' # Auto confirm when booked by receptionist
        )
        db.session.add(appt)
        db.session.commit()
        
        patient = Patient.query.get(patient_id)
        doctor = Doctor.query.get(doc_id)
        
        AuditService.log_action(current_user.id, f"Booked Appointment #{appt.id} (Front Desk) for Patient: {patient.full_name}")
        NotificationService.create_notification(
            patient.user_id,
            "Appointment Confirmed",
            f"Your appointment with {doctor.full_name} on {appt_date} at {slot} has been booked and confirmed by front desk."
        )
        NotificationService.create_notification(
            doctor.user_id,
            "New Appointment Confirmed",
            f"Front desk has booked an appointment for {patient.full_name} on {appt_date} at {slot}."
        )
        
        flash(f"Appointment booked and confirmed for {patient.full_name}!", 'success')
        return redirect(url_for('receptionist.dashboard'))
        
    return render_template('receptionist/book_appointment.html', form=form, patients=patients_list)

@receptionist_bp.route('/appointments/confirm/<int:id>', methods=['POST'])
def confirm_appointment(id):
    appt = Appointment.query.get_or_404(id)
    appt.status = 'Confirmed'
    db.session.commit()
    
    AuditService.log_action(current_user.id, f"Confirmed Appointment #{appt.id}")
    NotificationService.create_notification(
        appt.patient.user_id,
        "Appointment Confirmed",
        f"Your appointment with {appt.doctor.full_name} on {appt.appointment_date} at {appt.time_slot} has been confirmed."
    )
    
    flash(f"Appointment #{id} has been confirmed.", 'success')
    return redirect(request.referrer or url_for('receptionist.dashboard'))

@receptionist_bp.route('/appointments/cancel/<int:id>', methods=['POST'])
def cancel_appointment(id):
    appt = Appointment.query.get_or_404(id)
    appt.status = 'Cancelled'
    db.session.commit()
    
    AuditService.log_action(current_user.id, f"Cancelled Appointment #{appt.id}")
    NotificationService.create_notification(
        appt.patient.user_id,
        "Appointment Cancelled",
        f"Your appointment with {appt.doctor.full_name} on {appt.appointment_date} at {appt.time_slot} has been cancelled."
    )
    
    flash(f"Appointment #{id} has been cancelled.", 'warning')
    return redirect(request.referrer or url_for('receptionist.dashboard'))

@receptionist_bp.route('/billing', methods=['GET', 'POST'])
def generate_bill():
    form = GenerateBillForm()
    
    # Dynamically pre-populate consultation fee when patient/appointment selected
    # This can be processed in form submission
    if form.validate_on_submit():
        appt_id = form.appointment_id.data
        patient_id = form.patient_id.data
        
        # Check if bill already exists for appointment
        if appt_id and appt_id != 0:
            existing_bill = Bill.query.filter_by(appointment_id=appt_id).first()
            if existing_bill:
                flash(f"A bill already exists for Appointment #{appt_id}.", "warning")
                return redirect(url_for('receptionist.view_bill', id=existing_bill.id))
                
        bill = BillingService.generate_bill(
            appointment_id=appt_id,
            patient_id=patient_id,
            consultation_fee=form.consultation_fee.data,
            medicine_charges=form.medicine_charges.data,
            lab_charges=form.lab_charges.data,
            other_charges=form.other_charges.data,
            discount=form.discount.data,
            status=form.status.data
        )
        
        # If bill status is Paid, record payment
        if bill.status == 'Paid':
            BillingService.record_payment(bill.id, bill.grand_total, "Cash", "CASH-FRONT-DESK")
            
        AuditService.log_action(current_user.id, f"Generated Bill #{bill.id} for Patient: {bill.patient.full_name}")
        NotificationService.create_notification(
            bill.patient.user_id,
            "Invoice Generated",
            f"An invoice with Grand Total INR {bill.grand_total:.2f} has been generated. Status: {bill.status}."
        )
        
        flash(f"Bill generated successfully!", 'success')
        return redirect(url_for('receptionist.view_bill', id=bill.id))
        
    return render_template('receptionist/generate_bill.html', form=form)

@receptionist_bp.route('/bill/<int:id>')
def view_bill(id):
    bill = Bill.query.get_or_404(id)
    return render_template('receptionist/view_bill.html', bill=bill)

@receptionist_bp.route('/bill/<int:id>/pay', methods=['POST'])
def pay_bill(id):
    bill = Bill.query.get_or_404(id)
    method = request.form.get('payment_method', 'Cash')
    txn_id = request.form.get('transaction_id', f"TXN-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    
    BillingService.record_payment(bill.id, bill.grand_total, method, txn_id)
    AuditService.log_action(current_user.id, f"Recorded Payment for Bill #{bill.id}")
    flash(f"Payment of INR {bill.grand_total:.2f} recorded. Invoice status marked as Paid.", 'success')
    return redirect(url_for('receptionist.view_bill', id=bill.id))

@receptionist_bp.route('/download-bill-pdf/<int:id>')
def download_bill_pdf(id):
    bill = Bill.query.get_or_404(id)
    pdf_data = ReportService.generate_invoice_pdf(bill)
    return Response(
        pdf_data,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"inline;filename=invoice_mc_{bill.id:06d}.pdf"}
    )

@receptionist_bp.route('/patients')
def patients():
    search = request.args.get('search', '')
    query = Patient.query
    if search:
        query = query.filter(
            (Patient.first_name.like(f"%{search}%")) |
            (Patient.last_name.like(f"%{search}%")) |
            (Patient.phone.like(f"%{search}%"))
        )
    patients_list = query.all()
    return render_template('receptionist/patients.html', patients=patients_list, search=search)
