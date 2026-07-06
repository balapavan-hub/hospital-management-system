from flask_wtf import FlaskForm
from wtforms import SelectField, DateField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Optional
from app.models.department import Department
from app.models.user import Doctor

TIME_SLOTS = [
    ('', 'Select Time Slot'),
    ('09:00 AM - 09:30 AM', '09:00 AM - 09:30 AM'),
    ('09:30 AM - 10:00 AM', '09:30 AM - 10:00 AM'),
    ('10:00 AM - 10:30 AM', '10:00 AM - 10:30 AM'),
    ('10:30 AM - 11:00 AM', '10:30 AM - 11:00 AM'),
    ('11:00 AM - 11:30 AM', '11:00 AM - 11:30 AM'),
    ('11:30 AM - 12:00 PM', '11:30 AM - 12:00 PM'),
    ('12:00 PM - 12:30 PM', '12:00 PM - 12:30 PM'),
    ('12:30 PM - 01:00 PM', '12:30 PM - 01:00 PM'),
    ('02:00 PM - 02:30 PM', '02:00 PM - 02:30 PM'),
    ('02:30 PM - 03:00 PM', '02:30 PM - 03:00 PM'),
    ('03:00 PM - 03:30 PM', '03:00 PM - 03:30 PM'),
    ('03:30 PM - 04:00 PM', '03:30 PM - 04:00 PM'),
    ('04:00 PM - 04:30 PM', '04:00 PM - 04:30 PM'),
    ('04:30 PM - 05:00 PM', '04:30 PM - 05:00 PM')
]

class BookAppointmentForm(FlaskForm):
    department_id = SelectField('Department', coerce=int, validators=[
        DataRequired(message="Please select a department")
    ])
    doctor_id = SelectField('Doctor', coerce=int, validators=[
        DataRequired(message="Please select a doctor")
    ])
    appointment_date = DateField('Appointment Date', format='%Y-%m-%d', validators=[
        DataRequired(message="Please select a date")
    ])
    time_slot = SelectField('Time Slot', choices=TIME_SLOTS, validators=[
        DataRequired(message="Please select a time slot")
    ])
    reason = TextAreaField('Reason for Appointment / Symptoms', validators=[
        Optional()
    ])
    submit = SubmitField('Book Appointment')

    def __init__(self, *args, **kwargs):
        super(BookAppointmentForm, self).__init__(*args, **kwargs)
        # Populate departments choices
        self.department_id.choices = [(0, 'Select Department')] + [(d.id, d.name) for d in Department.query.order_by(Department.name).all()]
        # Populating doctors choices initially empty or all
        self.doctor_id.choices = [(0, 'Select Doctor')] + [(doc.id, f"{doc.full_name} ({doc.specialization})") for doc in Doctor.query.filter_by(availability_status='Available').all()]


class RescheduleAppointmentForm(FlaskForm):
    appointment_date = DateField('New Date', format='%Y-%m-%d', validators=[
        DataRequired(message="Please select a new date")
    ])
    time_slot = SelectField('New Time Slot', choices=TIME_SLOTS, validators=[
        DataRequired(message="Please select a time slot")
    ])
    submit = SubmitField('Reschedule Appointment')
