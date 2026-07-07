from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import db
from app.models.prescription import Prescription
from app.models.pharmacy import PharmacyMedicine, Supplier, PharmacySale, PharmacyPurchase
from app.models.user import Pharmacist, Patient
from app.services.audit_service import AuditService

pharmacist_bp = Blueprint('pharmacist', __name__)

@pharmacist_bp.before_request
@login_required
def pharmacist_required():
    if current_user.role != 'Pharmacist':
        flash('Unauthorized access! Pharmacist credentials required.', 'danger')
        return redirect(url_for('auth.login'))

@pharmacist_bp.route('/dashboard')
def dashboard():
    # Show active prescriptions in this hospital
    prescriptions = Prescription.query.filter_by(hospital_id=current_user.hospital_id).order_by(Prescription.created_at.desc()).all()
    return render_template('pharmacist/dashboard.html', prescriptions=prescriptions)

@pharmacist_bp.route('/inventory', methods=['GET', 'POST'])
def inventory():
    items = PharmacyMedicine.query.filter_by(hospital_id=current_user.hospital_id).order_by(PharmacyMedicine.item_name).all()
    suppliers = Supplier.query.filter_by(hospital_id=current_user.hospital_id).all()
    
    if request.method == 'POST':
        name = request.form.get('item_name', '').strip()
        category = request.form.get('category', '').strip()
        qty = request.form.get('quantity', '').strip()
        unit = request.form.get('unit', '').strip()
        min_lvl = request.form.get('min_stock_level', '').strip()
        p_price = request.form.get('purchase_price', '').strip()
        s_price = request.form.get('selling_price', '').strip()
        exp_date_str = request.form.get('expiry_date', '').strip()
        supp_id = request.form.get('supplier_id', '').strip()
        
        if not name or not category or not qty or not exp_date_str:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('pharmacist.inventory'))
            
        try:
            exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d').date()
            med = PharmacyMedicine(
                hospital_id=current_user.hospital_id,
                item_name=name,
                category=category,
                quantity=int(qty),
                unit=unit or 'units',
                min_stock_level=int(min_lvl) if min_lvl else 10,
                purchase_price=float(p_price) if p_price else 0.0,
                selling_price=float(s_price) if s_price else 0.0,
                expiry_date=exp_date,
                supplier_id=int(supp_id) if (supp_id and supp_id != '0') else None
            )
            db.session.add(med)
            db.session.commit()
            
            # Log purchase if quantity > 0
            if int(qty) > 0 and supp_id and supp_id != '0':
                purchase = PharmacyPurchase(
                    hospital_id=current_user.hospital_id,
                    medicine_id=med.id,
                    supplier_id=int(supp_id),
                    quantity=int(qty),
                    purchase_price=float(p_price) if p_price else 0.0,
                    total_cost=(int(qty) * (float(p_price) if p_price else 0.0))
                )
                db.session.add(purchase)
                db.session.commit()

            AuditService.log_action(current_user.id, f"Added Medicine '{med.item_name}' to inventory", request.remote_addr)
            flash('Medicine added successfully to inventory!', 'success')
            return redirect(url_for('pharmacist.inventory'))
            
        except ValueError:
            flash('Invalid date or number format entered.', 'danger')
            return redirect(url_for('pharmacist.inventory'))

    return render_template('pharmacist/inventory.html', items=items, suppliers=suppliers)

@pharmacist_bp.route('/inventory/edit/<int:id>', methods=['GET', 'POST'])
def edit_inventory(id):
    med = PharmacyMedicine.query.filter_by(id=id, hospital_id=current_user.hospital_id).first_or_404()
    suppliers = Supplier.query.filter_by(hospital_id=current_user.hospital_id).all()
    
    if request.method == 'POST':
        med.item_name = request.form.get('item_name', '').strip()
        med.category = request.form.get('category', '').strip()
        med.quantity = int(request.form.get('quantity', '0'))
        med.unit = request.form.get('unit', 'units').strip()
        med.min_stock_level = int(request.form.get('min_stock_level', '10'))
        med.purchase_price = float(request.form.get('purchase_price', '0.00'))
        med.selling_price = float(request.form.get('selling_price', '0.00'))
        
        exp_date_str = request.form.get('expiry_date', '').strip()
        if exp_date_str:
            med.expiry_date = datetime.strptime(exp_date_str, '%Y-%m-%d').date()
            
        supp_id = request.form.get('supplier_id', '')
        med.supplier_id = int(supp_id) if (supp_id and supp_id != '0') else None
        
        db.session.commit()
        AuditService.log_action(current_user.id, f"Updated Medicine ID {med.id} ({med.item_name})", request.remote_addr)
        flash('Medicine inventory updated successfully!', 'success')
        return redirect(url_for('pharmacist.inventory'))
        
    return render_template('pharmacist/edit_inventory.html', item=med, suppliers=suppliers)

@pharmacist_bp.route('/dispense/<int:prescription_id>', methods=['GET', 'POST'])
def dispense(prescription_id):
    prescription = Prescription.query.filter_by(id=prescription_id, hospital_id=current_user.hospital_id).first_or_404()
    
    if request.method == 'POST':
        # Dispense prescription
        # Loop through prescribed medicines and try to deduct stock
        insufficient_medicines = []
        for item in prescription.medicines:
            # Try to find medicine in stock
            med = PharmacyMedicine.query.filter_by(hospital_id=current_user.hospital_id).filter(PharmacyMedicine.item_name.like(f"%{item.medicine_name}%")).first()
            if not med or med.quantity < 1:
                insufficient_medicines.append(item.medicine_name)
                
        if insufficient_medicines:
            flash(f"Insufficient stock for prescribed medicines: {', '.join(insufficient_medicines)}. Please purchase stock first.", 'danger')
            return redirect(url_for('pharmacist.dispense', prescription_id=prescription.id))
            
        # If all in stock, deduct and record sales
        total_bill = 0.0
        for item in prescription.medicines:
            med = PharmacyMedicine.query.filter_by(hospital_id=current_user.hospital_id).filter(PharmacyMedicine.item_name.like(f"%{item.medicine_name}%")).first()
            # Deduct 1 unit pack per duration days (mock check: 1 pack)
            med.quantity -= 1
            
            # Log sale
            sale = PharmacySale(
                hospital_id=current_user.hospital_id,
                medicine_id=med.id,
                patient_id=prescription.patient_id,
                prescription_id=prescription.id,
                quantity=1,
                unit_price=med.selling_price,
                total_price=med.selling_price
            )
            db.session.add(sale)
            total_bill += float(med.selling_price)
            
        # Update associated Patient Bill if it exists
        if prescription.appointment and prescription.appointment.bill:
            bill = prescription.appointment.bill
            bill.medicine_charges = float(bill.medicine_charges) + total_bill
            bill.grand_total = float(bill.consultation_fee) + float(bill.medicine_charges) + float(bill.lab_charges) + float(bill.other_charges)
            # Apply GST
            bill.gst = round(bill.grand_total * 0.18, 2)
            bill.grand_total = round(bill.grand_total + bill.gst, 2)
            
        db.session.commit()
        AuditService.log_action(current_user.id, f"Dispensed medicines for Prescription #{prescription.id}", request.remote_addr)
        flash('Prescription medicines successfully dispensed and billed!', 'success')
        return redirect(url_for('pharmacist.dashboard'))
        
    return render_template('pharmacist/dispense.html', prescription=prescription)

@pharmacist_bp.route('/suppliers', methods=['GET', 'POST'])
def suppliers():
    suppliers_list = Supplier.query.filter_by(hospital_id=current_user.hospital_id).order_by(Supplier.name).all()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        contact = request.form.get('contact_person', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        addr = request.form.get('address', '').strip()
        
        if not name or not phone:
            flash('Supplier Name and Phone are required.', 'danger')
            return redirect(url_for('pharmacist.suppliers'))
            
        supplier = Supplier(
            hospital_id=current_user.hospital_id,
            name=name,
            contact_person=contact,
            phone=phone,
            email=email,
            address=addr
        )
        db.session.add(supplier)
        db.session.commit()
        
        AuditService.log_action(current_user.id, f"Added Supplier '{supplier.name}'", request.remote_addr)
        flash('Supplier registered successfully!', 'success')
        return redirect(url_for('pharmacist.suppliers'))
        
    return render_template('pharmacist/suppliers.html', suppliers=suppliers_list)
