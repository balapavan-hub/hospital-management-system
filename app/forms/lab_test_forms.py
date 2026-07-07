from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SelectField, TextAreaField, DecimalField, IntegerField, SelectMultipleField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange, Length

class DoctorOrderLabForm(FlaskForm):
    order_type = SelectField('Order Type', choices=[
        ('single', 'Single Test Template'),
        ('package', 'Predefined Test Package')
    ], validators=[DataRequired()])
    
    # These choices will be populated dynamically in the route
    single_template_id = SelectField('Select Test Template', coerce=int, validators=[Optional()])
    package_id = SelectField('Select Predefined Package', coerce=int, validators=[Optional()])
    
    description = TextAreaField('Special Instructions / Clinical Notes', validators=[Optional()])
    cost = DecimalField('Total Cost (INR)', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Submit Lab Order')

class LabPackageForm(FlaskForm):
    name = StringField('Package Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional()])
    cost = DecimalField('Package Cost (INR)', default=1000.00, validators=[DataRequired(), NumberRange(min=0)])
    # We will dynamically populate choices of this SelectMultipleField with LabTestTemplate choices
    templates = SelectMultipleField('Included Test Parameters', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Save Package')

class LabTestTemplateForm(FlaskForm):
    test_name = StringField('Test Parameter Name', validators=[DataRequired(), Length(max=100)])
    test_category = SelectField('Category', choices=[
        ('Blood Test', 'Blood Test'),
        ('Urine Test', 'Urine Test'),
        ('Imaging', 'Imaging (X-Ray/MRI/CT/Ultrasound)'),
        ('Cardiac', 'Cardiac (ECG/Echo/TMT)'),
        ('Pathology', 'Pathology / Biopsy'),
        ('Eye Test', 'Eye Test'),
        ('Pulmonary', 'Pulmonary Function Test'),
        ('Other', 'Other')
    ], validators=[DataRequired()])
    
    normal_range_min = DecimalField('Normal Range (Minimum)', validators=[Optional()])
    normal_range_max = DecimalField('Normal Range (Maximum)', validators=[Optional()])
    normal_range_text = StringField('Normal Range (Text Representation)', validators=[Optional(), Length(max=200)], description="e.g. 70-100 or 'Negative'")
    unit = StringField('Unit of Measurement', validators=[Optional(), Length(max=50)], placeholder="e.g. mg/dL, g/dL, %")
    
    age_min = IntegerField('Minimum Age', default=0, validators=[Optional(), NumberRange(min=0)])
    age_max = IntegerField('Maximum Age', default=120, validators=[Optional(), NumberRange(min=0)])
    gender = SelectField('Applicable Gender', choices=[
        ('Both', 'Both / Unisex'),
        ('Male', 'Male Only'),
        ('Female', 'Female Only')
    ], default='Both', validators=[DataRequired()])
    
    critical_range_min = DecimalField('Critical Range (Minimum)', validators=[Optional()])
    critical_range_max = DecimalField('Critical Range (Maximum)', validators=[Optional()])
    
    cost = DecimalField('Parameter Cost (INR)', default=200.00, validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Save Template')

class InventoryItemForm(FlaskForm):
    item_name = StringField('Item Name', validators=[DataRequired(), Length(max=100)])
    category = SelectField('Category', choices=[
        ('Reagent', 'Reagents'),
        ('Chemical', 'Chemicals'),
        ('Gloves', 'Gloves'),
        ('Masks', 'Masks'),
        ('Syringes', 'Syringes'),
        ('Blood Collection Tubes', 'Blood Collection Tubes'),
        ('Test Kits', 'Test Kits'),
        ('Consumable', 'Other Consumables')
    ], validators=[DataRequired()])
    quantity = IntegerField('Stock Quantity', default=0, validators=[DataRequired(), NumberRange(min=0)])
    unit = StringField('Stock Unit', default='pcs', validators=[DataRequired(), Length(max=50)])
    min_stock_level = IntegerField('Minimum Stock Level (Low Stock Alert)', default=10, validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Save Inventory Item')

class RecordLabResultsForm(FlaskForm):
    # This form is dynamically rendered. We will collect findings on the route side,
    # but we define these standard fields for technician reviews.
    remarks = TextAreaField('Technician Remarks', validators=[Optional()])
    interpretation = TextAreaField('Result Interpretation', validators=[Optional()])
    submit = SubmitField('Record and Complete Lab Test')
