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
from app.forms import PrescriptionForm, MedicalReportForm, DoctorOrderLabForm
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
    pending_tests = LabTest.query.filter_by(doctor_id=doctor.id).filter(~LabTest.status.in_(['Completed', 'Delivered', 'Cancelled'])).order_by(LabTest.test_date.desc()).all()
    completed_tests = LabTest.query.filter_by(doctor_id=doctor.id).filter(LabTest.status.in_(['Completed', 'Delivered'])).order_by(LabTest.result_date.desc()).all()
    return render_template('doctor/lab_tests.html', pending_tests=pending_tests, completed_tests=completed_tests)

@doctor_bp.route('/order-lab-test/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def order_lab_test(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    doctor = current_user.doctor
    form = DoctorOrderLabForm()
    
    # Load parameters and packages
    templates = LabTestTemplate.query.order_by(LabTestTemplate.test_name).all()
    packages = LabPackage.query.filter_by(is_active=True).order_by(LabPackage.name).all()
    
    form.single_template_id.choices = [(0, '--- Select Single Parameter ---')] + [(t.id, f"{t.test_name} (INR {t.cost})") for t in templates]
    form.package_id.choices = [(0, '--- Select Health Package ---')] + [(p.id, f"{p.name} (INR {p.cost})") for p in packages]
    
    if form.validate_on_submit():
        today_str = datetime.now().strftime('%Y%m%d')
        count_today = LabTest.query.filter(LabTest.sample_id.like(f"SAM-{today_str}-%")).count()
        sample_id = f"SAM-{today_str}-{(count_today + 1):04d}"
        
        test_name = ""
        test_category = ""
        single_template_id = None
        package_id = None
        
        if form.order_type.data == 'single':
            template = LabTestTemplate.query.get(form.single_template_id.data)
            if not template or form.single_template_id.data == 0:
                flash('Please select a valid test parameter.', 'danger')
                return render_template('doctor/order_lab_test.html', form=form, patient=patient)
            test_name = template.test_name
            test_category = template.test_category
            single_template_id = template.id
            cost = template.cost
        else:
            pkg = LabPackage.query.get(form.package_id.data)
            if not pkg or form.package_id.data == 0:
                flash('Please select a valid test package.', 'danger')
                return render_template('doctor/order_lab_test.html', form=form, patient=patient)
            test_name = pkg.name
            test_category = "Health Package"
            package_id = pkg.id
            cost = pkg.cost
            
        lab_test = LabTest(
            sample_id=sample_id,
            patient_id=patient.id,
            doctor_id=doctor.id,
            package_id=package_id,
            single_template_id=single_template_id,
            test_name=test_name,
            test_category=test_category,
            description=form.description.data,
            cost=form.cost.data or cost,
            status='Sample Collected'
        )
        db.session.add(lab_test)
        db.session.commit()
        
        AuditService.log_action(current_user.id, f"Ordered Lab Test/Package '{lab_test.test_name}' for Patient '{patient.full_name}'")
        
        NotificationService.create_notification(
            patient.user_id,
            "New Lab Test Ordered",
            f"Dr. {doctor.last_name} has ordered '{lab_test.test_name}' (Sample ID: {lab_test.sample_id})."
        )
        CommunicationService.send_mock_email(
            patient.user.email,
            "Lab Test Assigned",
            f"Hello {patient.full_name}, Dr. {doctor.full_name} has assigned you the lab test '{lab_test.test_name}'. Please visit the laboratory for sample collection."
        )
        
        # Create corresponding bill for lab test
        # We can integrate this into receptionist billing or log a bill immediately!
        # Let's create a pending bill for this patient for lab test
        from app.services.billing_service import BillingService
        BillingService.generate_bill(
            appointment_id=0,
            patient_id=patient.id,
            consultation_fee=0,
            medicine_charges=0,
            lab_charges=lab_test.cost,
            other_charges=0,
            discount=0,
            status='Pending'
        )
        CommunicationService.send_mock_email(
            patient.user.email,
            "Lab Test Bill Generated",
            f"Hello {patient.full_name}, a lab billing invoice has been generated for your ordered test '{lab_test.test_name}'. Amount: INR {lab_test.cost}."
        )

        flash(f"Laboratory order '{lab_test.test_name}' placed successfully! Sample ID: {sample_id}", 'success')
        return redirect(url_for('doctor.patient_details', patient_id=patient.id))
        
    return render_template('doctor/order_lab_test.html', form=form, patient=patient)

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

@doctor_bp.route('/patient-trends/<int:patient_id>')
def patient_trends(patient_id):
    patient = Patient.query.get_or_404(patient_id)
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
                
    return render_template('doctor/patient_trends.html', patient=patient, trends=trends, completed_tests=completed_tests)

