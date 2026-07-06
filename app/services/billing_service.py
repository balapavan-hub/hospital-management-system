from decimal import Decimal
from app.models import db
from app.models.billing import Bill, Payment

class BillingService:
    @staticmethod
    def calculate_bill_totals(consultation_fee, medicine_charges, lab_charges, other_charges, discount):
        """
        Calculate GST and Grand Total based on charges and discount.
        Uses 18% GST.
        """
        # Convert values to Decimal for precise calculation
        consultation = Decimal(str(consultation_fee or 0.00))
        medicine = Decimal(str(medicine_charges or 0.00))
        lab = Decimal(str(lab_charges or 0.00))
        other = Decimal(str(other_charges or 0.00))
        disc = Decimal(str(discount or 0.00))
        
        subtotal = consultation + medicine + lab + other
        
        # Calculate 18% GST on subtotal
        gst_amount = subtotal * Decimal('0.18')
        
        # Grand total calculation
        grand_total = (subtotal + gst_amount) - disc
        if grand_total < 0:
            grand_total = Decimal('0.00')
            
        return {
            'gst': round(gst_amount, 2),
            'grand_total': round(grand_total, 2)
        }

    @staticmethod
    def generate_bill(appointment_id, patient_id, consultation_fee=0, medicine_charges=0, lab_charges=0, other_charges=0, discount=0, status='Pending'):
        """
        Generate and persist a new bill in the database.
        """
        totals = BillingService.calculate_bill_totals(
            consultation_fee, medicine_charges, lab_charges, other_charges, discount
        )
        
        bill = Bill(
            appointment_id=appointment_id if appointment_id != 0 else None,
            patient_id=patient_id,
            consultation_fee=consultation_fee,
            medicine_charges=medicine_charges,
            lab_charges=lab_charges,
            other_charges=other_charges,
            gst=totals['gst'],
            discount=discount,
            grand_total=totals['grand_total'],
            status=status
        )
        
        db.session.add(bill)
        db.session.commit()
        return bill

    @staticmethod
    def record_payment(bill_id, amount, payment_method, transaction_id=None):
        """
        Record a payment for a bill and mark the bill as paid.
        """
        bill = Bill.query.get(bill_id)
        if not bill:
            return None
            
        payment = Payment(
            bill_id=bill_id,
            amount=amount,
            payment_method=payment_method,
            transaction_id=transaction_id
        )
        
        db.session.add(payment)
        
        # Mark bill status as Paid if total paid equals or exceeds grand_total
        # For simplicity, we just mark it paid once a payment is made.
        bill.status = 'Paid'
        db.session.commit()
        
        return payment
