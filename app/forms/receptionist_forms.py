from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, TextAreaField, DecimalField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Regexp, Optional, NumberRange, ValidationError
from app.models.user import User, Patient

class QuickRegisterPatientForm(FlaskForm):
    first_name = StringField('First Name', validators=[
        DataRequired(message="First name is required"),
        Length(min=2, max=50)
    ])
    last_name = StringField('Last Name', validators=[
        DataRequired(message="Last name is required"),
        Length(min=2, max=50)
    ])
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required"),
        Email(message="Invalid email address")
    ])
    phone = StringField('Phone Number', validators=[
        DataRequired(message="Phone number is required"),
        Regexp(r'^\+?[0-9]{10,15}$', message="Phone number must be between 10 to 15 digits")
    ])
    gender = SelectField('Gender', choices=[('', 'Select Gender'), ('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], validators=[
        DataRequired(message="Please select gender")
    ])
    date_of_birth = DateField('Date of Birth', format='%Y-%m-%d', validators=[
        DataRequired(message="Date of birth is required")
    ])
    blood_group = SelectField('Blood Group', choices=[
        ('', 'Select Blood Group'), 
        ('A+', 'A+'), ('A-', 'A-'), 
        ('B+', 'B+'), ('B-', 'B-'), 
        ('O+', 'O+'), ('O-', 'O-'), 
        ('AB+', 'AB+'), ('AB-', 'AB-')
    ], validators=[Optional()])
    address = TextAreaField('Address', validators=[Optional(), Length(max=255)])
    medical_history = TextAreaField('Medical History', validators=[Optional()])
    submit = SubmitField('Register Patient')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email address is already registered.')

    def validate_phone(self, phone):
        patient = Patient.query.filter_by(phone=phone.data).first()
        if patient:
            raise ValidationError('Phone number is already registered.')


class GenerateBillForm(FlaskForm):
    appointment_id = SelectField('Appointment (Optional)', coerce=int, validators=[Optional()])
    patient_id = SelectField('Patient', coerce=int, validators=[
        DataRequired(message="Please select a patient")
    ])
    consultation_fee = DecimalField('Consultation Fee (INR)', validators=[
        DataRequired(message="Consultation fee is required"),
        NumberRange(min=0)
    ], default=0.00)
    medicine_charges = DecimalField('Medicine Charges (INR)', validators=[
        DataRequired(message="Medicine charges are required"),
        NumberRange(min=0)
    ], default=0.00)
    lab_charges = DecimalField('Lab Charges (INR)', validators=[
        DataRequired(message="Lab charges are required"),
        NumberRange(min=0)
    ], default=0.00)
    other_charges = DecimalField('Other Charges (INR)', validators=[
        DataRequired(message="Other charges are required"),
        NumberRange(min=0)
    ], default=0.00)
    discount = DecimalField('Discount (INR)', validators=[
        DataRequired(message="Discount is required"),
        NumberRange(min=0)
    ], default=0.00)
    status = SelectField('Payment Status', choices=[
        ('Pending', 'Pending'),
        ('Paid', 'Paid')
    ], default='Pending')
    submit = SubmitField('Generate Bill & Print')

    def __init__(self, *args, **kwargs):
        super(GenerateBillForm, self).__init__(*args, **kwargs)
        # Populate patient list
        self.patient_id.choices = [(0, 'Select Patient')] + [(p.id, f"{p.full_name} ({p.phone})") for p in Patient.query.order_by(Patient.first_name).all()]
        
        # Populate appointment list (unbilled and confirmed/completed appointments)
        # Let's import inside constructor or keep it general
        from app.models.appointment import Appointment
        unbilled_appointments = Appointment.query.filter(
            Appointment.status.in_(['Confirmed', 'Completed']),
            ~Appointment.id.in_([
                # select bills where appointment_id is not null
                # we'll dynamically query it
            ])
        ).all()
        self.appointment_id.choices = [(0, 'No Specific Appointment')] + [(a.id, f"Appt #{a.id} - Date: {a.appointment_date} (Patient: {a.patient.full_name})") for a in unbilled_appointments]
