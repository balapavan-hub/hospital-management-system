from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SelectField, TextAreaField, DecimalField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange

class OrderLabTestForm(FlaskForm):
    test_category = SelectField('Test Category', choices=[
        ('Blood Test', 'Blood Test'),
        ('Urine Test', 'Urine Test'),
        ('Imaging', 'Imaging (X-Ray / MRI / CT Scan / Ultrasound)'),
        ('Cardiac', 'Cardiac (ECG / Echo / Stress Test)'),
        ('Pathology', 'Pathology / Biopsy'),
        ('Eye Test', 'Eye Test'),
        ('Pulmonary', 'Pulmonary Function Test'),
        ('Other', 'Other')
    ], validators=[DataRequired()])
    test_name = SelectField('Test Name', choices=[
        ('Complete Blood Count (CBC)', 'Complete Blood Count (CBC)'),
        ('Blood Sugar (Fasting)', 'Blood Sugar (Fasting)'),
        ('Blood Sugar (PP)', 'Blood Sugar (Post Prandial)'),
        ('HbA1c', 'HbA1c (Glycated Hemoglobin)'),
        ('Lipid Profile', 'Lipid Profile'),
        ('Liver Function Test (LFT)', 'Liver Function Test (LFT)'),
        ('Kidney Function Test (KFT)', 'Kidney Function Test (KFT)'),
        ('Thyroid Profile (T3, T4, TSH)', 'Thyroid Profile (T3, T4, TSH)'),
        ('Hemoglobin (Hb)', 'Hemoglobin (Hb)'),
        ('Blood Pressure Check', 'Blood Pressure Check'),
        ('Blood Group & Rh Typing', 'Blood Group & Rh Typing'),
        ('Urine Routine & Microscopy', 'Urine Routine & Microscopy'),
        ('Urine Culture', 'Urine Culture'),
        ('X-Ray Chest', 'X-Ray Chest (PA View)'),
        ('X-Ray Spine', 'X-Ray Spine'),
        ('X-Ray Limb', 'X-Ray Limb / Joint'),
        ('MRI Brain', 'MRI Brain'),
        ('MRI Spine', 'MRI Spine'),
        ('MRI Knee / Joint', 'MRI Knee / Joint'),
        ('CT Scan Head', 'CT Scan Head'),
        ('CT Scan Chest', 'CT Scan Chest'),
        ('CT Scan Abdomen', 'CT Scan Abdomen'),
        ('Ultrasound Abdomen', 'Ultrasound Abdomen'),
        ('Ultrasound Pelvis', 'Ultrasound Pelvis'),
        ('ECG', 'Electrocardiogram (ECG)'),
        ('Echocardiography', 'Echocardiography (2D Echo)'),
        ('Stress Test (TMT)', 'Stress Test (TMT)'),
        ('Biopsy', 'Biopsy'),
        ('Pap Smear', 'Pap Smear'),
        ('Eye Examination', 'Eye Examination'),
        ('Pulmonary Function Test', 'Pulmonary Function Test'),
        ('Other', 'Other (Specify in Description)')
    ], validators=[DataRequired()])
    description = TextAreaField('Additional Instructions / Notes', validators=[Optional()])
    cost = DecimalField('Test Cost (INR)', default=500.00, validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Order Lab Test')

class UpdateLabResultForm(FlaskForm):
    result_value = TextAreaField('Test Result / Findings', validators=[DataRequired()])
    normal_range = StringField('Normal Reference Range', validators=[Optional()])
    unit = StringField('Unit (e.g. mg/dL, mmol/L)', validators=[Optional()])
    result_status = SelectField('Result Status', choices=[
        ('Normal', 'Normal'),
        ('Abnormal', 'Abnormal'),
        ('Critical', 'Critical')
    ], validators=[DataRequired()])
    remarks = TextAreaField('Remarks / Interpretation', validators=[Optional()])
    report_file = FileField('Attach Report File (PDF/Image)', validators=[Optional(), FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'Only PDF and Image files allowed.')])
    submit = SubmitField('Save Results')
