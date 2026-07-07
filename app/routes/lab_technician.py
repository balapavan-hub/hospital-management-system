import os
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.models import db
from app.models.lab_test import LabTest, LabTestResult, LabInventory
from app.models.user import Patient, Doctor, LabTechnician
from app.forms.lab_test_forms import InventoryItemForm, RecordLabResultsForm
from app.services import AuditService, AlertService, CommunicationService, NotificationService

lab_technician_bp = Blueprint('lab_technician', __name__)

@lab_technician_bp.before_request
@login_required
def technician_required():
    if current_user.role != 'LabTechnician':
        flash('Unauthorized access! You do not have permission to view this page.', 'danger')
        return redirect(url_for('auth.login'))

@lab_technician_bp.route('/dashboard')
def dashboard():
    tech = current_user.lab_technician
    if not tech:
        # Auto-create profile if user exists but profile does not
        tech = LabTechnician(
            user_id=current_user.id,
            hospital_id=current_user.hospital_id,
            first_name="Lab",
            last_name="Technician",
            phone="9999999999",
            employee_id=f"EMP-LT-{current_user.id:04d}"
        )
        db.session.add(tech)
        db.session.commit()
        
    total_processed = LabTest.query.filter_by(hospital_id=current_user.hospital_id, lab_technician_id=tech.id).filter(LabTest.status.in_(['Completed', 'Delivered'])).count()
    pending_samples = LabTest.query.filter_by(hospital_id=current_user.hospital_id).filter(LabTest.status != 'Completed', LabTest.status != 'Delivered').count()
    low_stock_items = LabInventory.query.filter_by(hospital_id=current_user.hospital_id).filter(LabInventory.quantity <= LabInventory.min_stock_level).all()
    
    recent_orders = LabTest.query.filter_by(hospital_id=current_user.hospital_id).order_by(LabTest.test_date.desc()).limit(10).all()

    return render_template(
        'lab_technician/dashboard.html',
        tech=tech,
        total_processed=total_processed,
        pending_samples=pending_samples,
        low_stock_count=len(low_stock_items),
        low_stock_items=low_stock_items,
        recent_orders=recent_orders
    )

@lab_technician_bp.route('/orders')
def orders():
    status_filter = request.args.get('status', '')
    query = LabTest.query.filter_by(hospital_id=current_user.hospital_id)
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    orders_list = query.order_by(LabTest.test_date.desc()).all()
    return render_template('lab_technician/orders.html', orders=orders_list, status_filter=status_filter)

@lab_technician_bp.route('/process-sample/<int:test_id>', methods=['POST'])
def process_sample(test_id):
    lab_test = LabTest.query.filter_by(id=test_id, hospital_id=current_user.hospital_id).first_or_404()
    tech = current_user.lab_technician
    
    current_status = lab_test.status
    statuses = ['Sample Collected', 'Sample Received', 'Under Processing', 'Quality Check', 'Completed', 'Report Generated', 'Delivered']
    
    if current_status not in statuses:
        flash('Invalid sample status.', 'danger')
        return redirect(url_for('lab_technician.orders'))
        
    idx = statuses.index(current_status)
    if idx < len(statuses) - 1:
        next_status = statuses[idx + 1]
        
        # Assign technician if not assigned
        if not lab_test.lab_technician_id:
            lab_test.lab_technician_id = tech.id
            
        lab_test.status = next_status
        db.session.commit()
        
        AuditService.log_action(current_user.id, f"Updated Lab Test status to '{next_status}' (Sample ID: {lab_test.sample_id})")
        
        # Trigger Communication alerts
        if next_status == 'Sample Received':
            CommunicationService.send_mock_email(
                lab_test.patient.user.email,
                "Lab Sample Received",
                f"Hello {lab_test.patient.full_name}, your sample for test '{lab_test.test_name}' has been received and is under processing."
            )
        elif next_status == 'Delivered':
            CommunicationService.send_mock_sms(
                lab_test.patient.phone,
                f"Hello {lab_test.patient.full_name}, your lab report for {lab_test.test_name} (Sample ID: {lab_test.sample_id}) has been delivered."
            )

        flash(f"Status updated to: {next_status}", 'success')
    else:
        flash('Test is already completed or delivered.', 'info')
        
    return redirect(url_for('lab_technician.orders'))

@lab_technician_bp.route('/record-results/<int:test_id>', methods=['GET', 'POST'])
def record_results(test_id):
    lab_test = LabTest.query.filter_by(id=test_id, hospital_id=current_user.hospital_id).first_or_404()
    tech = current_user.lab_technician
    
    # Load all parameters
    templates = []
    if lab_test.package:
        templates = lab_test.package.templates
    elif lab_test.single_template:
        templates = [lab_test.single_template]
        
    if request.method == 'POST':
        # Delete existing results for re-entry
        LabTestResult.query.filter_by(lab_test_id=lab_test.id).delete()
        
        for t in templates:
            obs_val = request.form.get(f"observed_{t.id}", "").strip()
            if not obs_val:
                flash(f"Please fill in observed value for parameter: {t.test_name}", 'danger')
                return redirect(url_for('lab_technician.record_results', test_id=lab_test.id))
            
            result = LabTestResult(
                lab_test_id=lab_test.id,
                template_id=t.id,
                observed_value=obs_val,
                normal_range_used=t.normal_range_text or (f"{t.normal_range_min}-{t.normal_range_max}" if (t.normal_range_min is not None) else "N/A"),
                unit_used=t.unit or ""
            )
            # Compare limits
            result.result_status = AlertService.check_result_limits(result)
            db.session.add(result)
            
        lab_test.status = 'Completed'
        lab_test.result_date = datetime.utcnow()
        lab_test.lab_technician_id = tech.id
        lab_test.remarks = request.form.get('remarks', '').strip()
        lab_test.interpretation = request.form.get('interpretation', '').strip()
        
        db.session.commit()
        
        # Trigger Alerts and generate PDF/QR
        AlertService.process_lab_test_alerts(lab_test)
        
        # Generate PDF Report (and QR verification code)
        from app.services.report_service import ReportService
        pdf_filename = ReportService.generate_lab_report_pdf(lab_test)
        lab_test.report_file = pdf_filename
        db.session.commit()
        
        AuditService.log_action(current_user.id, f"Recorded results and completed lab test '{lab_test.test_name}'")
        
        # Notifications
        NotificationService.create_notification(
            lab_test.patient.user_id,
            "Lab Report Completed",
            f"Your laboratory results for '{lab_test.test_name}' are ready. Status: {'Critical' if lab_test.is_critical else 'Normal'}."
        )
        CommunicationService.send_mock_email(
            lab_test.patient.user.email,
            "Lab Test Results Completed",
            f"Hello {lab_test.patient.full_name}, your lab results for {lab_test.test_name} are completed and available in your portal."
        )
        
        flash('Lab results successfully recorded, report PDF and QR Code generated.', 'success')
        return redirect(url_for('lab_technician.orders'))

    existing_results = {r.template_id: r.observed_value for r in lab_test.results}
    
    return render_template(
        'lab_technician/record_results.html',
        lab_test=lab_test,
        templates=templates,
        existing_results=existing_results
    )

@lab_technician_bp.route('/inventory', methods=['GET', 'POST'])
def inventory():
    items = LabInventory.query.filter_by(hospital_id=current_user.hospital_id).order_by(LabInventory.item_name).all()
    form = InventoryItemForm()
    
    if form.validate_on_submit():
        item = LabInventory(
            hospital_id=current_user.hospital_id,
            item_name=form.item_name.data.strip(),
            category=form.category.data,
            quantity=form.quantity.data,
            unit=form.unit.data.strip(),
            min_stock_level=form.min_stock_level.data
        )
        db.session.add(item)
        db.session.commit()
        AuditService.log_action(current_user.id, f"Added inventory item: {item.item_name}")
        flash('Inventory item added successfully!', 'success')
        return redirect(url_for('lab_technician.inventory'))
        
    return render_template('lab_technician/inventory.html', items=items, form=form)

@lab_technician_bp.route('/inventory/edit/<int:id>', methods=['GET', 'POST'])
def edit_inventory(id):
    item = LabInventory.query.filter_by(id=id, hospital_id=current_user.hospital_id).first_or_404()
    form = InventoryItemForm(obj=item)
    
    if form.validate_on_submit():
        item.item_name = form.item_name.data.strip()
        item.category = form.category.data
        item.quantity = form.quantity.data
        item.unit = form.unit.data.strip()
        item.min_stock_level = form.min_stock_level.data
        
        db.session.commit()
        AuditService.log_action(current_user.id, f"Updated inventory item: {item.item_name}")
        flash('Inventory item updated successfully!', 'success')
        return redirect(url_for('lab_technician.inventory'))
        
    return render_template('lab_technician/edit_inventory.html', item=item, form=form)

@lab_technician_bp.route('/inventory/delete/<int:id>', methods=['POST'])
def delete_inventory(id):
    item = LabInventory.query.filter_by(id=id, hospital_id=current_user.hospital_id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    AuditService.log_action(current_user.id, f"Deleted inventory item: {item.item_name}")
    flash('Inventory item deleted successfully!', 'success')
    return redirect(url_for('lab_technician.inventory'))
