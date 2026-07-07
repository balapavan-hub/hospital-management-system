from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import db
from app.models.appointment import Appointment
from app.models.user import Patient, Nurse
from app.services.audit_service import AuditService

nurse_bp = Blueprint('nurse', __name__)

@nurse_bp.before_request
@login_required
def nurse_required():
    if current_user.role != 'Nurse':
        flash('Unauthorized access! Nurse credentials required.', 'danger')
        return redirect(url_for('auth.login'))

@nurse_bp.route('/dashboard')
def dashboard():
    nurse = current_user.nurse
    if not nurse:
        # Auto-create profile if user exists but profile does not
        nurse = Nurse(
            user_id=current_user.id,
            hospital_id=current_user.hospital_id,
            first_name="Hospital",
            last_name="Nurse",
            phone="9876543212"
        )
        db.session.add(nurse)
        db.session.commit()

    today = date.today()
    
    # Retrieve today's appointments for this hospital
    appointments = Appointment.query.filter_by(
        hospital_id=current_user.hospital_id,
        appointment_date=today
    ).order_by(Appointment.time_slot).all()
    
    return render_template(
        'nurse/dashboard.html',
        nurse=nurse,
        appointments=appointments
    )

@nurse_bp.route('/record-vitals/<int:appointment_id>', methods=['GET', 'POST'])
def record_vitals(appointment_id):
    appointment = Appointment.query.filter_by(
        id=appointment_id,
        hospital_id=current_user.hospital_id
    ).first_or_404()
    
    if request.method == 'POST':
        bp = request.form.get('blood_pressure', '').strip()
        pulse = request.form.get('pulse', '').strip()
        temp = request.form.get('temperature', '').strip()
        height = request.form.get('height', '').strip()
        weight = request.form.get('weight', '').strip()
        observations = request.form.get('observations', '').strip()
        
        # Validations
        if not bp or not pulse or not temp or not height or not weight:
            flash('Please fill in all vitals fields.', 'danger')
            return redirect(url_for('nurse.record_vitals', appointment_id=appointment.id))
            
        try:
            pulse_int = int(pulse)
            temp_float = float(temp)
            height_float = float(height) # in cm
            weight_float = float(weight) # in kg
            
            # Compute BMI
            height_m = height_float / 100.0
            bmi_val = round(weight_float / (height_m * height_m), 2)
            
            appointment.vitals_blood_pressure = bp
            appointment.vitals_pulse = pulse_int
            appointment.vitals_temperature = temp_float
            appointment.vitals_height = height_float
            appointment.vitals_weight = weight_float
            appointment.vitals_bmi = bmi_val
            appointment.nurse_observations = observations
            appointment.vitals_recorded_at = datetime.utcnow()
            
            db.session.commit()
            AuditService.log_action(current_user.id, f"Recorded vitals for Appointment #{appointment.id} (Patient: {appointment.patient.full_name})", request.remote_addr)
            flash(f"Vitals for Patient {appointment.patient.full_name} recorded successfully!", 'success')
            return redirect(url_for('nurse.dashboard'))
            
        except ValueError:
            flash('Invalid numeric values entered for pulse, temperature, height, or weight.', 'danger')
            return redirect(url_for('nurse.record_vitals', appointment_id=appointment.id))
            
    return render_template('nurse/vitals_form.html', appointment=appointment)
