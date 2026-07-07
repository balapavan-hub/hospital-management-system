from datetime import date, datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, Response
from flask_login import login_required, current_user

from app.models import db
from app.models.hospital import Hospital
from app.models.user import Doctor, Patient
from app.models.department import Department
from app.models.appointment import Appointment
from app.models.prescription import Prescription
from app.models.medical_report import MedicalReport
from app.models.billing import Bill
from app.models.lab_test import LabTest
from app.forms import BookAppointmentForm, RescheduleAppointmentForm
from app.services import AppointmentService, AuditService, NotificationService, ReportService

patient_bp = Blueprint('patient', __name__)

@patient_bp.before_request
@login_required
def patient_required():
    if current_user.role != 'Patient':
        flash('Unauthorized access! You do not have permission to view this page.', 'danger')
        return redirect(url_for('auth.login'))

@patient_bp.route('/dashboard')
def dashboard():
    patient = current_user.patient
    if not patient:
        # Auto-create profile if user exists but profile does not
        patient = Patient(
            user_id=current_user.id,
            first_name="General",
            last_name="Patient",
            phone="9876543210",
            gender="Male",
            date_of_birth=date(1990, 1, 1)
        )
        db.session.add(patient)
        db.session.commit()
        
    today = date.today()
    
    # Retrieve all medical history, visits, prescriptions, bills globally across all hospitals
    upcoming_appointments = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.appointment_date >= today,
        Appointment.status.in_(['Pending', 'Confirmed'])
    ).order_by(Appointment.appointment_date, Appointment.time_slot).all()
    
    past_appointments = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        (Appointment.appointment_date < today) | (Appointment.status.in_(['Completed', 'Cancelled']))
    ).order_by(Appointment.appointment_date.desc()).limit(10).all()
    
    prescriptions = Prescription.query.filter_by(patient_id=patient.id).order_by(Prescription.created_at.desc()).limit(10).all()
    bills = Bill.query.filter_by(patient_id=patient.id).order_by(Bill.created_at.desc()).all()
    reports = MedicalReport.query.filter_by(patient_id=patient.id).order_by(MedicalReport.upload_date.desc()).all()
    lab_tests = LabTest.query.filter_by(patient_id=patient.id).order_by(LabTest.test_date.desc()).all()

    return render_template(
        'patient/dashboard.html',
        patient=patient,
        upcoming_appointments=upcoming_appointments,
        past_appointments=past_appointments,
        prescriptions=prescriptions,
        bills=bills,
        reports=reports,
        lab_tests=lab_tests
    )

@patient_bp.route('/search-hospitals')
def search_hospitals():
    state_filter = request.args.get('state', '').strip()
    city_filter = request.args.get('city', '').strip()
    type_filter = request.args.get('type', '').strip()
    search_q = request.args.get('search', '').strip()
    
    query = Hospital.query.filter_by(status='Approved')
    
    if state_filter:
        query = query.filter(Hospital.state.like(f"%{state_filter}%"))
    if city_filter:
        query = query.filter(Hospital.city.like(f"%{city_filter}%"))
    if type_filter:
        query = query.filter_by(hospital_type=type_filter)
    if search_q:
        query = query.filter(
            (Hospital.name.like(f"%{search_q}%")) |
            (Hospital.address.like(f"%{search_q}%"))
        )
        
    hospitals_list = query.all()
    
    # Distinct states and cities for filter dropdowns
    states = db.session.query(Hospital.state).filter_by(status='Approved').distinct().all()
    cities = db.session.query(Hospital.city).filter_by(status='Approved').distinct().all()
    
    return render_template(
        'patient/search_hospitals.html',
        hospitals=hospitals_list,
        states=[s[0] for s in states],
        cities=[c[0] for c in cities],
        selected_state=state_filter,
        selected_city=city_filter,
        selected_type=type_filter,
        search_query=search_q
    )

@patient_bp.route('/book-appointment', methods=['GET', 'POST'])
def book_appointment():
    patient = current_user.patient
    form = BookAppointmentForm()
    
    hospital_id = request.args.get('hospital_id', type=int)
    if not hospital_id:
        # Fallback to first approved hospital
        hosp = Hospital.query.filter_by(status='Approved').first()
        hospital_id = hosp.id if hosp else 1
        
    hospital = Hospital.query.get_or_404(hospital_id)
    
    # Load departments and doctors inside the selected hospital
    departments = Department.query.filter_by(hospital_id=hospital_id).all()
    form.doctor_id.choices = [(d.id, d.full_name) for d in Doctor.query.filter_by(hospital_id=hospital_id).all()]
    
    if form.validate_on_submit():
        doc_id = form.doctor_id.data
        appt_date = form.appointment_date.data
        slot = form.time_slot.data
        
        # Check slot availability
        if not AppointmentService.is_slot_available(doc_id, appt_date, slot):
            flash('The selected time slot is no longer available. Please select a different slot.', 'danger')
            return render_template('patient/book_appointment.html', form=form, hospital=hospital, departments=departments)
            
        doctor = Doctor.query.get(doc_id)
        
        # Create Appointment
        appt = Appointment(
            hospital_id=hospital_id,
            patient_id=patient.id,
            doctor_id=doc_id,
            appointment_date=appt_date,
            time_slot=slot,
            reason=form.reason.data,
            status='Pending'
        )
        db.session.add(appt)
        db.session.commit()
        
        # Audit & Notification
        AuditService.log_action(current_user.id, f"Booked Appointment #{appt.id} with {doctor.full_name} at Hospital '{hospital.name}'")
        NotificationService.create_notification(
            current_user.id,
            "Appointment Booked Successfully",
            f"Your appointment with {doctor.full_name} at {hospital.name} is booked for {appt_date} at {slot}. Status: Pending Confirmation."
        )
        NotificationService.create_notification(
            doctor.user_id,
            "New Appointment Request",
            f"Patient {patient.full_name} has requested an appointment on {appt_date} at {slot}."
        )
        
        flash(f'Your appointment request at {hospital.name} has been submitted successfully!', 'success')
        return redirect(url_for('patient.dashboard'))
        
    return render_template('patient/book_appointment.html', form=form, hospital=hospital, departments=departments)

@patient_bp.route('/cancel-appointment/<int:id>', methods=['POST'])
def cancel_appointment(id):
    patient = current_user.patient
    appt = Appointment.query.get_or_404(id)
    
    if appt.patient_id != patient.id:
        flash('Unauthorized cancellation request.', 'danger')
        return redirect(url_for('patient.dashboard'))
        
    if appt.status in ['Completed', 'Cancelled']:
        flash('Appointment is already completed or cancelled.', 'warning')
        return redirect(url_for('patient.dashboard'))
        
    appt.status = 'Cancelled'
    db.session.commit()
    
    AuditService.log_action(current_user.id, f"Cancelled Appointment #{appt.id}")
    
    # Notify Doctor
    NotificationService.create_notification(
        appt.doctor.user_id,
        "Appointment Cancelled by Patient",
        f"Patient {patient.full_name} has cancelled their appointment scheduled for {appt.appointment_date} at {appt.time_slot}."
    )
    
    flash('Appointment has been cancelled.', 'warning')
    return redirect(url_for('patient.dashboard'))

@patient_bp.route('/reschedule-appointment/<int:id>', methods=['GET', 'POST'])
def reschedule_appointment(id):
    patient = current_user.patient
    appt = Appointment.query.get_or_404(id)
    
    if appt.patient_id != patient.id:
        flash('Unauthorized rescheduling request.', 'danger')
        return redirect(url_for('patient.dashboard'))
        
    if appt.status in ['Completed', 'Cancelled']:
        flash('Cannot reschedule completed or cancelled appointments.', 'warning')
        return redirect(url_for('patient.dashboard'))
        
    form = RescheduleAppointmentForm()
    
    if form.validate_on_submit():
        new_date = form.appointment_date.data
        new_slot = form.time_slot.data
        
        if not AppointmentService.is_slot_available(appt.doctor_id, new_date, new_slot, exclude_appointment_id=appt.id):
            flash('The selected time slot is not available. Please choose another.', 'danger')
            return render_template('patient/reschedule_form.html', form=form, appointment=appt)
            
        old_date = appt.appointment_date
        old_slot = appt.time_slot
        
        appt.appointment_date = new_date
        appt.time_slot = new_slot
        appt.status = 'Pending' # Reset to pending upon reschedule
        db.session.commit()
        
        AuditService.log_action(current_user.id, f"Rescheduled Appointment #{appt.id}")
        
        # Notify Doctor
        NotificationService.create_notification(
            appt.doctor.user_id,
            "Appointment Rescheduled by Patient",
            f"Patient {patient.full_name} rescheduled appointment from {old_date} ({old_slot}) to {new_date} ({new_slot})."
        )
        
        flash('Appointment rescheduled successfully. Pending doctor confirmation.', 'success')
        return redirect(url_for('patient.dashboard'))
        
    elif request.method == 'GET':
        form.appointment_date.data = appt.appointment_date
        form.time_slot.data = appt.time_slot
        
    return render_template('patient/reschedule_form.html', form=form, appointment=appt)

@patient_bp.route('/download-prescription-pdf/<int:id>')
def download_prescription_pdf(id):
    pres = Prescription.query.get_or_404(id)
    if pres.patient_id != current_user.patient.id:
        flash('Unauthorized access to this prescription.', 'danger')
        return redirect(url_for('patient.dashboard'))
        
    pdf_data = ReportService.generate_prescription_pdf(pres)
    return Response(
        pdf_data,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment;filename=prescription_mc_{pres.id:05d}.pdf"}
    )

@patient_bp.route('/download-bill-pdf/<int:id>')
def download_bill_pdf(id):
    bill = Bill.query.get_or_404(id)
    if bill.patient_id != current_user.patient.id:
        flash('Unauthorized access to this bill.', 'danger')
        return redirect(url_for('patient.dashboard'))
        
    pdf_data = ReportService.generate_invoice_pdf(bill)
    return Response(
        pdf_data,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment;filename=invoice_mc_{bill.id:06d}.pdf"}
    )

# --- AJAX APIs ---
@patient_bp.route('/api/get-departments/<int:hospital_id>')
def api_get_departments(hospital_id):
    depts = Department.query.filter_by(hospital_id=hospital_id).all()
    return jsonify([
        {'id': d.id, 'name': d.name} for d in depts
    ])

@patient_bp.route('/api/get-doctors/<int:dept_id>')
def api_get_doctors(dept_id):
    # This was a previous route. For safety we support both dept_id filtering and hospital_id filtering.
    docs = Doctor.query.filter_by(department_id=dept_id, availability_status='Available').all()
    return jsonify([
        {'id': d.id, 'name': d.full_name, 'specialization': d.specialization} for d in docs
    ])

@patient_bp.route('/api/get-doctors/<int:hospital_id>/<int:dept_id>')
def api_get_hospital_doctors(hospital_id, dept_id):
    docs = Doctor.query.filter_by(hospital_id=hospital_id, department_id=dept_id, availability_status='Available').all()
    return jsonify([
        {'id': d.id, 'name': d.full_name, 'specialization': d.specialization} for d in docs
    ])

@patient_bp.route('/api/get-booked-slots/<int:doctor_id>/<string:date_str>')
def api_get_booked_slots(doctor_id, date_str):
    try:
        query_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify([]), 400
        
    booked_slots = AppointmentService.get_booked_slots(doctor_id, query_date)
    return jsonify(booked_slots)

# --- LAB TESTS ---
@patient_bp.route('/lab-tests')
def lab_tests():
    patient = current_user.patient
    if not patient:
        flash('Patient profile not found!', 'danger')
        return redirect(url_for('main.index'))
    
    pending_tests = LabTest.query.filter_by(patient_id=patient.id).filter(~LabTest.status.in_(['Completed', 'Delivered', 'Cancelled'])).order_by(LabTest.test_date.desc()).all()
    completed_tests = LabTest.query.filter_by(patient_id=patient.id).filter(LabTest.status.in_(['Completed', 'Delivered'])).order_by(LabTest.result_date.desc()).all()
    
    return render_template('patient/lab_tests.html', pending_tests=pending_tests, completed_tests=completed_tests)

@patient_bp.route('/view-lab-result/<int:test_id>')
def view_lab_result(test_id):
    lab_test = LabTest.query.get_or_404(test_id)
    if lab_test.patient_id != current_user.patient.id:
        flash('Unauthorized access to this lab test.', 'danger')
        return redirect(url_for('patient.dashboard'))
    return render_template('patient/view_lab_result.html', lab_test=lab_test)

@patient_bp.route('/lab-trends')
def lab_trends():
    patient = current_user.patient
    if not patient:
        flash('Patient profile not found!', 'danger')
        return redirect(url_for('main.index'))
        
    completed_tests = LabTest.query.filter_by(patient_id=patient.id).filter(LabTest.status.in_(['Completed', 'Delivered'])).order_by(LabTest.result_date.asc()).all()
    
    # Structure data for Chart.js
    trends = {}
    for test in completed_tests:
        for result in test.results:
            param_name = result.template.test_name
            try:
                val = float(result.observed_value)
                if param_name not in trends:
                    trends[param_name] = {'dates': [], 'values': [], 'unit': result.unit_used or ''}
                trends[param_name]['dates'].append(test.result_date.strftime('%d-%b-%Y'))
                trends[param_name]['values'].append(val)
            except ValueError:
                continue
                
    return render_template('patient/lab_trends.html', trends=trends, completed_tests=completed_tests)
