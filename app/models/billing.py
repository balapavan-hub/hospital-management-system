from datetime import datetime
from app.models import db

class Bill(db.Model):
    __tablename__ = 'bills'
    
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id', ondelete='SET NULL'), unique=True, nullable=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False)
    consultation_fee = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    medicine_charges = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    lab_charges = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    other_charges = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    gst = db.Column(db.Numeric(10, 2), nullable=False, default=0.00) # Standard 18% GST or computed amount
    discount = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    grand_total = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    status = db.Column(db.Enum('Paid', 'Pending', name='billing_status'), default='Pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    payments = db.relationship('Payment', backref='bill', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Bill {self.id} (Status: {self.status}, Total: {self.grand_total})>"


class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bills.id', ondelete='CASCADE'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False) # Cash, Card, UPI, Insurance
    transaction_id = db.Column(db.String(100), unique=True, nullable=True)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Payment {self.id} for Bill {self.bill_id}>"
