from datetime import date, datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, Response
from flask_login import login_required, current_user

from app.models import db
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
        flash('Patient profile not found!', 'danger')
        return redirect(url_for('main.index'))
        
    today = date.today()
    
    # Queries
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

@patient_bp.route('/book-appointment', methods=['GET', 'POST'])
def book_appointment():
    patient = current_user.patient
    form = BookAppointmentForm()
    
    if form.validate_on_submit():
        doc_id = form.doctor_id.data
        appt_date = form.appointment_date.data
        slot = form.time_slot.data
        
        # Check slot availability
        if not AppointmentService.is_slot_available(doc_id, appt_date, slot):
            flash('The selected time slot is no longer available. Please select a different slot.', 'danger')
            return render_template('patient/book_appointment.html', form=form)
            
        # Create Appointment
        appt = Appointment(
            patient_id=patient.id,
            doctor_id=doc_id,
            appointment_date=appt_date,
            time_slot=slot,
            reason=form.reason.data,
            status='Pending'
        )
        db.session.add(appt)
        db.session.commit()
        
        doctor = Doctor.query.get(doc_id)
        
        # Audit & Notification
        AuditService.log_action(current_user.id, f"Booked Appointment #{appt.id} with {doctor.full_name}")
        NotificationService.create_notification(
            current_user.id,
            "Appointment Booked Successfully",
            f"Your appointment with {doctor.full_name} is booked for {appt_date} at {slot}. Status: Pending Confirmation."
        )
        NotificationService.create_notification(
            doctor.user_id,
            "New Appointment Request",
            f"Patient {patient.full_name} has requested an appointment on {appt_date} at {slot}."
        )
        
        flash('Your appointment request has been submitted successfully!', 'success')
        return redirect(url_for('patient.dashboard'))
        
    return render_template('patient/book_appointment.html', form=form)

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
@patient_bp.route('/api/get-doctors/<int:dept_id>')
def api_get_doctors(dept_id):
    docs = Doctor.query.filter_by(department_id=dept_id, availability_status='Available').all()
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
    
    pending_tests = LabTest.query.filter_by(patient_id=patient.id).filter(LabTest.status != 'Completed', LabTest.status != 'Cancelled').order_by(LabTest.test_date.desc()).all()
    completed_tests = LabTest.query.filter_by(patient_id=patient.id, status='Completed').order_by(LabTest.result_date.desc()).all()
    
    return render_template('patient/lab_tests.html', pending_tests=pending_tests, completed_tests=completed_tests)

@patient_bp.route('/view-lab-result/<int:test_id>')
def view_lab_result(test_id):
    lab_test = LabTest.query.get_or_404(test_id)
    if lab_test.patient_id != current_user.patient.id:
        flash('Unauthorized access to this lab test.', 'danger')
        return redirect(url_for('patient.dashboard'))
    return render_template('patient/view_lab_result.html', lab_test=lab_test)
