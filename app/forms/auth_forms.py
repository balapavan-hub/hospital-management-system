from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SelectField, DateField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, Regexp, ValidationError
from app.models.user import User, Patient

class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required"), 
        Email(message="Invalid email address")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required")
    ])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class PatientRegisterForm(FlaskForm):
    first_name = StringField('First Name', validators=[
        DataRequired(message="First name is required"),
        Length(min=2, max=50, message="First name must be between 2 and 50 characters")
    ])
    last_name = StringField('Last Name', validators=[
        DataRequired(message="Last name is required"),
        Length(min=2, max=50, message="Last name must be between 2 and 50 characters")
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
        DataRequired(message="Password is required"),
        Length(min=6, message="Password must be at least 6 characters long")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message="Please confirm your password"),
        EqualTo('password', message="Passwords must match")
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
    medical_history = TextAreaField('Medical History (Allergies, chronic conditions, etc.)', validators=[Optional()])
    submit = SubmitField('Register')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email address is already registered.')

    def validate_phone(self, phone):
        patient = Patient.query.filter_by(phone=phone.data).first()
        if patient:
            raise ValidationError('Phone number is already registered.')


class ForgotPasswordForm(FlaskForm):
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required"),
        Email(message="Invalid email address")
    ])
    submit = SubmitField('Send Password Reset Link')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[
        DataRequired(message="Password is required"),
        Length(min=6, message="Password must be at least 6 characters long")
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(message="Please confirm your password"),
        EqualTo('password', message="Passwords must match")
    ])
    submit = SubmitField('Reset Password')


class UpdateProfileForm(FlaskForm):
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required"),
        Email(message="Invalid email address")
    ])
    phone = StringField('Phone Number', validators=[
        DataRequired(message="Phone number is required"),
        Regexp(r'^\+?[0-9]{10,15}$', message="Phone number must be between 10 to 15 digits")
    ])
    address = TextAreaField('Address', validators=[Optional(), Length(max=255)])
    medical_history = TextAreaField('Medical History', validators=[Optional()])
    profile_photo = FileField('Upload Profile Photo', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')
    ])
    submit = SubmitField('Update Profile')

    def __init__(self, current_user, *args, **kwargs):
        super(UpdateProfileForm, self).__init__(*args, **kwargs)
        self.current_user = current_user

    def validate_email(self, email):
        if email.data != self.current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Email address is already in use.')

    def validate_phone(self, phone):
        if self.current_user.role == 'Patient' and self.current_user.patient:
            if phone.data != self.current_user.patient.phone:
                p = Patient.query.filter_by(phone=phone.data).first()
                if p:
                    raise ValidationError('Phone number is already in use.')


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Current Password', validators=[
        DataRequired(message="Current password is required")
    ])
    new_password = PasswordField('New Password', validators=[
        DataRequired(message="New password is required"),
        Length(min=6, message="New password must be at least 6 characters long")
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(message="Please confirm your password"),
        EqualTo('new_password', message="Passwords must match")
    ])
    submit = SubmitField('Change Password')


class HospitalRegisterForm(FlaskForm):
    # Hospital Info
    hospital_name = StringField('Hospital Name', validators=[
        DataRequired(message="Hospital name is required"),
        Length(min=3, max=150)
    ])
    registration_number = StringField('Registration / License Number', validators=[
        DataRequired(message="Registration number is required"),
        Length(max=100)
    ])
    hospital_type = SelectField('Hospital Type', choices=[
        ('Private', 'Private'),
        ('Government', 'Government'),
        ('Clinic', 'Clinic'),
        ('Speciality Hospital', 'Speciality Hospital')
    ], validators=[DataRequired()])
    address = TextAreaField('Address', validators=[DataRequired()])
    state = StringField('State', validators=[DataRequired(), Length(max=100)])
    district = StringField('District', validators=[DataRequired(), Length(max=100)])
    city = StringField('City', validators=[DataRequired(), Length(max=100)])
    pincode = StringField('Pincode', validators=[
        DataRequired(),
        Regexp(r'^[0-9]{6}$', message="Pincode must be exactly 6 digits")
    ])
    email = StringField('Hospital Email', validators=[
        DataRequired(),
        Email(message="Invalid email address")
    ])
    phone = StringField('Hospital Phone', validators=[
        DataRequired(),
        Regexp(r'^\+?[0-9]{10,15}$', message="Phone number must be between 10 to 15 digits")
    ])
    website = StringField('Website', validators=[Optional(), Length(max=150)])
    logo = FileField('Hospital Logo (PNG/JPG)', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    license_document = FileField('License Document (PDF/PDF/Images)', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'pdf'], 'Images or PDF only!')
    ])

    submit = SubmitField('Submit Registration')
            
    def validate_registration_number(self, registration_number):
        from app.models.hospital import Hospital
        hosp = Hospital.query.filter_by(registration_number=registration_number.data).first()
        if hosp:
            raise ValidationError('Registration number is already registered.')

