from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, TextAreaField, DateField, SubmitField
from wtforms.validators import DataRequired, Optional, Length

class PrescriptionForm(FlaskForm):
    symptoms = TextAreaField('Symptoms / Patient Complaints', validators=[
        DataRequired(message="Symptoms are required")
    ])
    diagnosis = TextAreaField('Diagnosis', validators=[
        DataRequired(message="Diagnosis is required")
    ])
    remarks = TextAreaField('Doctor Remarks / Lifestyle advice', validators=[Optional()])
    follow_up_date = DateField('Follow-up Date', format='%Y-%m-%d', validators=[Optional()])
    submit = SubmitField('Save Prescription & Print')


class MedicalReportForm(FlaskForm):
    report_name = StringField('Report Name (e.g. CBC Blood Test, Head MRI)', validators=[
        DataRequired(message="Report name is required"),
        Length(min=2, max=100)
    ])
    report_file = FileField('Upload PDF Report File', validators=[
        FileRequired(message="Please select a file to upload"),
        FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'Only PDF or Image reports are allowed!')
    ])
    submit = SubmitField('Upload Report')
