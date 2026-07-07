from datetime import datetime
from app.models import db

# Many-to-Many helper table for Packages and Test Templates
lab_package_tests = db.Table('lab_package_tests',
    db.Column('package_id', db.Integer, db.ForeignKey('lab_packages.id', ondelete='CASCADE'), primary_key=True),
    db.Column('template_id', db.Integer, db.ForeignKey('lab_test_templates.id', ondelete='CASCADE'), primary_key=True)
)

class LabPackage(db.Model):
    __tablename__ = 'lab_packages'
    
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    cost = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Unique constraint per hospital
    __table_args__ = (
        db.UniqueConstraint('hospital_id', 'name', name='unique_hospital_package'),
    )

    # Relationships
    templates = db.relationship('LabTestTemplate', secondary=lab_package_tests, backref='packages')
    lab_tests = db.relationship('LabTest', backref='package')

    def __repr__(self):
        return f"<LabPackage {self.name}>"

class LabTestTemplate(db.Model):
    __tablename__ = 'lab_test_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id', ondelete='CASCADE'), nullable=False)
    test_name = db.Column(db.String(100), nullable=False)
    test_category = db.Column(db.String(100), nullable=False) # Blood Test, Urine Test, Imaging, etc.
    normal_range_min = db.Column(db.Float, nullable=True)
    normal_range_max = db.Column(db.Float, nullable=True)
    normal_range_text = db.Column(db.String(200), nullable=True)
    unit = db.Column(db.String(50), nullable=True)
    age_min = db.Column(db.Integer, nullable=True, default=0)
    age_max = db.Column(db.Integer, nullable=True, default=150)
    gender = db.Column(db.String(10), nullable=True, default='Both') # Male, Female, Both
    critical_range_min = db.Column(db.Float, nullable=True)
    critical_range_max = db.Column(db.Float, nullable=True)
    cost = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Unique constraint per hospital
    __table_args__ = (
        db.UniqueConstraint('hospital_id', 'test_name', name='unique_hospital_template'),
    )

    def __repr__(self):
        return f"<LabTestTemplate {self.test_name}>"

class LabTest(db.Model):
    __tablename__ = 'lab_tests'
    
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id', ondelete='CASCADE'), nullable=False)
    sample_id = db.Column(db.String(50), unique=True, nullable=False) # e.g. SAM-YYYYMMDD-XXXX
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id', ondelete='SET NULL'), nullable=True)
    lab_technician_id = db.Column(db.Integer, db.ForeignKey('lab_technicians.id', ondelete='SET NULL'), nullable=True)
    package_id = db.Column(db.Integer, db.ForeignKey('lab_packages.id', ondelete='SET NULL'), nullable=True)
    single_template_id = db.Column(db.Integer, db.ForeignKey('lab_test_templates.id', ondelete='SET NULL'), nullable=True)
    
    test_name = db.Column(db.String(150), nullable=False)
    test_category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='Sample Collected')
    test_date = db.Column(db.DateTime, default=datetime.utcnow)
    result_date = db.Column(db.DateTime, nullable=True)
    cost = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    payment_status = db.Column(db.String(50), default='Pending')
    is_critical = db.Column(db.Boolean, default=False)
    remarks = db.Column(db.Text, nullable=True)
    interpretation = db.Column(db.Text, nullable=True)
    report_file = db.Column(db.String(255), nullable=True)
    qr_code_path = db.Column(db.String(255), nullable=True)

    # Relationships
    results = db.relationship('LabTestResult', backref='lab_test', cascade="all, delete-orphan")
    single_template = db.relationship('LabTestTemplate')

    def __repr__(self):
        return f"<LabTest {self.test_name} ({self.sample_id})>"

class LabTestResult(db.Model):
    __tablename__ = 'lab_test_results'
    
    id = db.Column(db.Integer, primary_key=True)
    lab_test_id = db.Column(db.Integer, db.ForeignKey('lab_tests.id', ondelete='CASCADE'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('lab_test_templates.id', ondelete='CASCADE'), nullable=False)
    observed_value = db.Column(db.String(100), nullable=False)
    result_status = db.Column(db.String(50), default='Normal')
    normal_range_used = db.Column(db.String(200), nullable=True)
    unit_used = db.Column(db.String(50), nullable=True)

    # Relationships
    template = db.relationship('LabTestTemplate')

    def __repr__(self):
        return f"<LabTestResult {self.id} for LabTest {self.lab_test_id}>"

class LabInventory(db.Model):
    __tablename__ = 'lab_inventory'
    
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id', ondelete='CASCADE'), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    unit = db.Column(db.String(50), nullable=False, default='units')
    min_stock_level = db.Column(db.Integer, nullable=False, default=10)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint per hospital
    __table_args__ = (
        db.UniqueConstraint('hospital_id', 'item_name', name='unique_hospital_inventory'),
    )

    def __repr__(self):
        return f"<LabInventory {self.item_name}>"
