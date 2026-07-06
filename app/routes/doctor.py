import os
from datetime import date, datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, current_app, Response
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.models import db
from app.models.user import Doctor, Patient
from app.models.appointment import Appointment
from app.models.prescription import Prescription, PrescriptionMedicine
from app.models.medical_report import MedicalReport
from app.models.billing import Bill
from app.models.lab_test import LabTest
from app.forms import PrescriptionForm, MedicalReportForm, OrderLabTestForm, UpdateLabResultForm
from app.services import AuditService, NotificationService, ReportService

doctor_bp = Blueprint('doctor', __name__)

@doctor_bp.before_request
@login_required
def doctor_required():
    if current_user.role != 'Doctor':
        flash('Unauthorized access! You do not have permission to view this page.', 'danger')
        return redirect(url_for('auth.login'))

@doctor_bp.route('/dashboard')
def dashboard():
    doctor = current_user.doctor
    if not doctor:
        flash('Doctor profile not found!', 'danger')
        return redirect(url_for('main.index'))
        
    today = date.today()
    
    # Filter appointments
    today_appointments = Appointment.query.filter_by(doctor_id=doctor.id, appointment_date=today).filter(Appointment.status != 'Cancelled').order_by(Appointment.time_slot).all()
    upcoming_appointments = Appointment.query.filter(Appointment.doctor_id == doctor.id, Appointment.appointment_date > today, Appointment.status != 'Cancelled').order_by(Appointment.appointment_date, Appointment.time_slot).limit(10).all()
    completed_appointments = Appointment.query.filter_by(doctor_id=doctor.id, status='Completed').order_by(Appointment.appointment_date.desc()).limit(10).all()
    
    # Stats
    stats = {
        'today_count': len(today_appointments),
        'upcoming_count': Appointment.query.filter(Appointment.doctor_id == doctor.id, Appointment.appointment_date > today, Appointment.status != 'Cancelled').count(),
        'completed_count': Appointment.query.filter_by(doctor_id=doctor.id, status='Completed').count()
    }

    return render_template(
        'doctor/dashboard.html',
        today_appointments=today_appointments,
        upcoming_appointments=upcoming_appointments,
        completed_appointments=completed_appointments,
        stats=stats
    )

@doctor_bp.route('/patients')
def patients():
    search = request.args.get('search', '')
    doctor = current_user.doctor
    
    # Get patients who have had appointments with this doctor
    query = Patient.query.join(Appointment).filter(Appointment.doctor_id == doctor.id).distinct()
    
    if search:
        query = query.filter(
            (Patient.first_name.like(f"%{search}%")) |
            (Patient.last_name.like(f"%{search}%")) |
            (Patient.phone.like(f"%{search}%"))
        )
        
    patients_list = query.all()
    return render_template('doctor/patients.html', patients=patients_list, search=search)

@doctor_bp.route('/patient-details/<int:patient_id>')
def patient_details(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    doctor = current_user.doctor
    
    # Check if patient is associated with this doctor (for security/audit)
    appts = Appointment.query.filter_by(doctor_id=doctor.id, patient_id=patient.id).order_by(Appointment.appointment_date.desc()).all()
    prescriptions = Prescription.query.filter_by(doctor_id=doctor.id, patient_id=patient.id).order_by(Prescription.created_at.desc()).all()
    reports = MedicalReport.query.filter_by(patient_id=patient.id).order_by(MedicalReport.upload_date.desc()).all()
    lab_tests = LabTest.query.filter_by(patient_id=patient.id).order_by(LabTest.test_date.desc()).all()
    
    return render_template(
        'doctor/patient_details.html',
        patient=patient,
        appointments=appts,
        prescriptions=prescriptions,
        reports=reports,
        lab_tests=lab_tests
    )

@doctor_bp.route('/write-prescription/<int:appointment_id>', methods=['GET', 'POST'])
def write_prescription(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)
    doctor = current_user.doctor
    
    if appt.doctor_id != doctor.id:
        flash('Unauthorized access to this appointment.', 'danger')
        return redirect(url_for('doctor.dashboard'))
        
    form = PrescriptionForm()
    
    if form.validate_on_submit():
        # Create prescription
        prescription = Prescription(
            appointment_id=appt.id,
            doctor_id=doctor.id,
            patient_id=appt.patient_id,
            symptoms=form.symptoms.data,
            diagnosis=form.diagnosis.data,
            remarks=form.remarks.data,
            follow_up_date=form.follow_up_date.data
        )
        db.session.add(prescription)
        db.session.flush() # Populate prescription.id
        
        # Get medicines from list dynamically
        medicine_names = request.form.getlist('medicine_name[]')
        morning_doses = request.form.getlist('dosage_morning[]') # list of indices or 'on'/'off'
        afternoon_doses = request.form.getlist('dosage_afternoon[]')
        night_doses = request.form.getlist('dosage_night[]')
        durations = request.form.getlist('duration_days[]')
        
        # In frontend, indices match length of medicine_names
        for i in range(len(medicine_names)):
            if not medicine_names[i].strip():
                continue
                
            # Parse checkbox inputs
            m_dose = request.form.get(f'med_{i}_morning') == 'on'
            a_dose = request.form.get(f'med_{i}_afternoon') == 'on'
            n_dose = request.form.get(f'med_{i}_night') == 'on'
            
            try:
                days = int(durations[i])
            except ValueError:
                days = 5
                
            med = PrescriptionMedicine(
                prescription_id=prescription.id,
                medicine_name=medicine_names[i],
                dosage_morning=m_dose,
                dosage_afternoon=a_dose,
                dosage_night=n_dose,
                duration_days=days
            )
            db.session.add(med)
            
        # Update appointment status to Completed
        appt.status = 'Completed'
        db.session.commit()
        
        # Auditing & Notifications
        AuditService.log_action(current_user.id, f"Wrote prescription for Patient: {appt.patient.full_name}")
        NotificationService.create_notification(
            appt.patient.user_id,
            "New Prescription Added",
            f"Dr. {doctor.last_name} has uploaded a new prescription for your visit on {appt.appointment_date}."
        )
        
        flash('Prescription generated successfully!', 'success')
        return redirect(url_for('doctor.patient_details', patient_id=appt.patient_id))
        
    return render_template('doctor/prescription_form.html', form=form, appointment=appt)

@doctor_bp.route('/upload-report/<int:patient_id>', methods=['GET', 'POST'])
def upload_report(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    form = MedicalReportForm()
    
    if form.validate_on_submit():
        file = form.report_file.data
        filename = secure_filename(f"report_{patient.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
        filepath = os.path.join(current_app.config['REPORTS_FOLDER'], filename)
        file.save(filepath)
        
        report = MedicalReport(
            patient_id=patient.id,
            doctor_id=current_user.doctor.id,
            report_name=form.report_name.data,
            file_path=filename
        )
        db.session.add(report)
        db.session.commit()
        
        AuditService.log_action(current_user.id, f"Uploaded Medical Report '{report.report_name}' for Patient '{patient.full_name}'")
        NotificationService.create_notification(
            patient.user_id,
            "New Medical Report Available",
            f"Dr. {current_user.doctor.last_name} has uploaded a medical report: {report.report_name}."
        )
        
        flash('Medical report uploaded successfully!', 'success')
        return redirect(url_for('doctor.patient_details', patient_id=patient.id))
        
    return render_template('doctor/upload_report_form.html', form=form, patient=patient)

@doctor_bp.route('/download-report/<int:id>')
def download_report(id):
    report = MedicalReport.query.get_or_404(id)
    filepath = os.path.join(current_app.config['REPORTS_FOLDER'], report.file_path)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=report.report_name + os.path.splitext(report.file_path)[1])
    else:
        flash('File not found on server.', 'danger')
        return redirect(request.referrer or url_for('doctor.dashboard'))

@doctor_bp.route('/view-prescription-pdf/<int:id>')
def download_prescription_pdf(id):
    pres = Prescription.query.get_or_404(id)
    # Check if patient or consulting doctor is requesting
    if current_user.role == 'Doctor' and pres.doctor_id != current_user.doctor.id:
        flash('Unauthorized access to this prescription.', 'danger')
        return redirect(url_for('doctor.dashboard'))
        
    pdf_data = ReportService.generate_prescription_pdf(pres)
    return Response(
        pdf_data,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"inline;filename=prescription_mc_{pres.id:05d}.pdf"}
    )

@doctor_bp.route('/view-bills')
def view_bills():
    doctor = current_user.doctor
    # Retrieve all bills for appointments consultation fee matching this doctor
    bills = Bill.query.join(Appointment).filter(Appointment.doctor_id == doctor.id).all()
    return render_template('doctor/bills.html', bills=bills)

# --- LAB TESTS ---
@doctor_bp.route('/lab-tests')
def lab_tests():
    doctor = current_user.doctor
    pending_tests = LabTest.query.filter_by(doctor_id=doctor.id).filter(LabTest.status != 'Completed', LabTest.status != 'Cancelled').order_by(LabTest.test_date.desc()).all()
    completed_tests = LabTest.query.filter_by(doctor_id=doctor.id, status='Completed').order_by(LabTest.result_date.desc()).all()
    return render_template('doctor/lab_tests.html', pending_tests=pending_tests, completed_tests=completed_tests)

@doctor_bp.route('/order-lab-test/<int:patient_id>', methods=['GET', 'POST'])
def order_lab_test(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    doctor = current_user.doctor
    form = OrderLabTestForm()
    
    if form.validate_on_submit():
        lab_test = LabTest(
            patient_id=patient.id,
            doctor_id=doctor.id,
            test_name=form.test_name.data,
            test_category=form.test_category.data,
            description=form.description.data,
            cost=form.cost.data,
            status='Ordered'
        )
        db.session.add(lab_test)
        db.session.commit()
        
        AuditService.log_action(current_user.id, f"Ordered Lab Test '{lab_test.test_name}' for Patient '{patient.full_name}'")
        NotificationService.create_notification(
            patient.user_id,
            "Lab Test Ordered",
            f"Dr. {doctor.last_name} has ordered a {lab_test.test_name} test for you. Please visit the lab for sample collection."
        )
        
        flash(f"Lab test '{lab_test.test_name}' ordered successfully!", 'success')
        return redirect(url_for('doctor.patient_details', patient_id=patient.id))
        
    return render_template('doctor/order_lab_test.html', form=form, patient=patient)

@doctor_bp.route('/update-lab-result/<int:test_id>', methods=['GET', 'POST'])
def update_lab_result(test_id):
    lab_test = LabTest.query.get_or_404(test_id)
    doctor = current_user.doctor
    
    if lab_test.doctor_id != doctor.id:
        flash('Unauthorized access to this lab test.', 'danger')
        return redirect(url_for('doctor.lab_tests'))
    
    form = UpdateLabResultForm()
    
    if form.validate_on_submit():
        lab_test.result_value = form.result_value.data
        lab_test.normal_range = form.normal_range.data
        lab_test.unit = form.unit.data
        lab_test.result_status = form.result_status.data
        lab_test.remarks = form.remarks.data
        lab_test.status = 'Completed'
        lab_test.result_date = datetime.now()
        
        # Handle file upload
        if form.report_file.data:
            file = form.report_file.data
            filename = secure_filename(f"labtest_{lab_test.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            filepath = os.path.join(current_app.config['REPORTS_FOLDER'], filename)
            file.save(filepath)
            lab_test.report_file = filename
        
        db.session.commit()
        
        AuditService.log_action(current_user.id, f"Updated Lab Result for Test #{lab_test.id} ({lab_test.test_name})")
        NotificationService.create_notification(
            lab_test.patient.user_id,
            "Lab Test Result Available",
            f"Results for your {lab_test.test_name} test are now available. Status: {lab_test.result_status}."
        )
        
        flash(f"Lab test results for '{lab_test.test_name}' saved successfully!", 'success')
        return redirect(url_for('doctor.view_lab_result', test_id=lab_test.id))
    
    elif request.method == 'GET' and lab_test.result_value:
        form.result_value.data = lab_test.result_value
        form.normal_range.data = lab_test.normal_range
        form.unit.data = lab_test.unit
        form.result_status.data = lab_test.result_status
        form.remarks.data = lab_test.remarks
    
    return render_template('doctor/update_lab_result.html', form=form, lab_test=lab_test)

@doctor_bp.route('/view-lab-result/<int:test_id>')
def view_lab_result(test_id):
    lab_test = LabTest.query.get_or_404(test_id)
    return render_template('doctor/view_lab_result.html', lab_test=lab_test)

@doctor_bp.route('/download-lab-report/<int:test_id>')
def download_lab_report(test_id):
    lab_test = LabTest.query.get_or_404(test_id)
    if not lab_test.report_file:
        flash('No report file attached to this test.', 'warning')
        return redirect(request.referrer or url_for('doctor.lab_tests'))
    filepath = os.path.join(current_app.config['REPORTS_FOLDER'], lab_test.report_file)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=f"{lab_test.test_name}{os.path.splitext(lab_test.report_file)[1]}")
    else:
        flash('File not found on server.', 'danger')
        return redirect(request.referrer or url_for('doctor.lab_tests'))
