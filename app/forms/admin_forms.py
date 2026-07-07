from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, TextAreaField, DecimalField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp, Optional, ValidationError, NumberRange
from app.models.user import User, Doctor, Receptionist, LabTechnician
from app.models.department import Department
from app.models.room import Room

class DoctorForm(FlaskForm):
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
    password = PasswordField('Password', validators=[
        Optional(),
        Length(min=6, message="Password must be at least 6 characters long")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        EqualTo('password', message="Passwords must match")
    ])
    department_id = SelectField('Department', coerce=int, validators=[
        DataRequired(message="Please select department")
    ])
    specialization = StringField('Specialization', validators=[
        DataRequired(message="Specialization is required"),
        Length(max=100)
    ])
    qualification = StringField('Qualification', validators=[
        DataRequired(message="Qualification is required"),
        Length(max=100)
    ])
    consultation_fee = DecimalField('Consultation Fee (INR)', validators=[
        DataRequired(message="Consultation fee is required"),
        NumberRange(min=0, message="Fee cannot be negative")
    ])
    bio = TextAreaField('Doctor Bio', validators=[Optional()])
    availability_status = SelectField('Availability Status', choices=[
        ('Available', 'Available'),
        ('On Leave', 'On Leave'),
        ('Busy', 'Busy')
    ], default='Available')
    submit = SubmitField('Save Doctor')

    def __init__(self, doctor_id=None, *args, **kwargs):
        super(DoctorForm, self).__init__(*args, **kwargs)
        self.doctor_id = doctor_id
        # Dynamic departments dropdown
        self.department_id.choices = [(d.id, d.name) for d in Department.query.order_by(Department.name).all()]

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            # If editing and email belongs to this doctor, skip validation error
            if self.doctor_id:
                doctor = Doctor.query.get(self.doctor_id)
                if doctor and doctor.user_id == user.id:
                    return
            raise ValidationError('Email is already registered by another user.')

    def validate_phone(self, phone):
        doctor = Doctor.query.filter_by(phone=phone.data).first()
        if doctor:
            if self.doctor_id and doctor.id == self.doctor_id:
                return
            raise ValidationError('Phone number is already in use.')


class ReceptionistForm(FlaskForm):
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
    password = PasswordField('Password', validators=[
        Optional(),
        Length(min=6, message="Password must be at least 6 characters long")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        EqualTo('password', message="Passwords must match")
    ])
    shift = SelectField('Shift', choices=[
        ('Day', 'Day Shift (8 AM - 4 PM)'),
        ('Evening', 'Evening Shift (4 PM - 12 AM)'),
        ('Night', 'Night Shift (12 AM - 8 AM)')
    ], default='Day')
    submit = SubmitField('Save Receptionist')

    def __init__(self, receptionist_id=None, *args, **kwargs):
        super(ReceptionistForm, self).__init__(*args, **kwargs)
        self.receptionist_id = receptionist_id

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            if self.receptionist_id:
                receptionist = Receptionist.query.get(self.receptionist_id)
                if receptionist and receptionist.user_id == user.id:
                    return
            raise ValidationError('Email is already registered by another user.')

    def validate_phone(self, phone):
        receptionist = Receptionist.query.filter_by(phone=phone.data).first()
        if receptionist:
            if self.receptionist_id and receptionist.id == self.receptionist_id:
                return
            raise ValidationError('Phone number is already in use.')


class DepartmentForm(FlaskForm):
    name = StringField('Department Name', validators=[
        DataRequired(message="Department name is required"),
        Length(min=2, max=100)
    ])
    description = TextAreaField('Description', validators=[Optional()])
    icon_name = StringField('Icon Name (Bootstrap Icons class, e.g., bi-heart-pulse)', validators=[
        DataRequired(message="Icon class name is required"),
        Length(max=50)
    ], default='bi-hospital')
    submit = SubmitField('Save Department')

    def __init__(self, dept_id=None, *args, **kwargs):
        super(DepartmentForm, self).__init__(*args, **kwargs)
        self.dept_id = dept_id

    def validate_name(self, name):
        dept = Department.query.filter_by(name=name.data).first()
        if dept:
            if self.dept_id and dept.id == self.dept_id:
                return
            raise ValidationError('Department name already exists.')


class RoomForm(FlaskForm):
    room_number = StringField('Room Number', validators=[
        DataRequired(message="Room number is required"),
        Length(max=20)
    ])
    room_type = SelectField('Room Type', choices=[
        ('General Ward', 'General Ward'),
        ('Semi-Private', 'Semi-Private'),
        ('Private Room', 'Private Room'),
        ('ICU', 'Intensive Care Unit (ICU)'),
        ('Operation Theater', 'Operation Theater (OT)')
    ], validators=[DataRequired()])
    status = SelectField('Status', choices=[
        ('Available', 'Available'),
        ('Occupied', 'Occupied'),
        ('Under Maintenance', 'Under Maintenance')
    ], default='Available')
    rate_per_day = DecimalField('Rate Per Day (INR)', validators=[
        DataRequired(message="Daily rate is required"),
        NumberRange(min=0, message="Rate cannot be negative")
    ])
    submit = SubmitField('Save Room')

    def __init__(self, room_id=None, *args, **kwargs):
        super(RoomForm, self).__init__(*args, **kwargs)
        self.room_id = room_id

    def validate_room_number(self, room_number):
        room = Room.query.filter_by(room_number=room_number.data).first()
        if room:
            if self.room_id and room.id == self.room_id:
                return
            raise ValidationError('Room number already exists.')


class LabTechnicianForm(FlaskForm):
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
    password = PasswordField('Password', validators=[
        Optional(),
        Length(min=6, message="Password must be at least 6 characters long")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        EqualTo('password', message="Passwords must match")
    ])
    employee_id = StringField('Employee ID', validators=[
        DataRequired(message="Employee ID is required"),
        Length(min=2, max=50)
    ])
    submit = SubmitField('Save Lab Technician')

    def __init__(self, technician_id=None, *args, **kwargs):
        super(LabTechnicianForm, self).__init__(*args, **kwargs)
        self.technician_id = technician_id

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            if self.technician_id:
                technician = LabTechnician.query.get(self.technician_id)
                if technician and technician.user_id == user.id:
                    return
            raise ValidationError('Email is already registered by another user.')

    def validate_phone(self, phone):
        technician = LabTechnician.query.filter_by(phone=phone.data).first()
        if technician:
            if self.technician_id and technician.id == self.technician_id:
                return
            raise ValidationError('Phone number is already in use.')

    def validate_employee_id(self, employee_id):
        technician = LabTechnician.query.filter_by(employee_id=employee_id.data).first()
        if technician:
            if self.technician_id and technician.id == self.technician_id:
                return
            raise ValidationError('Employee ID is already assigned.')
