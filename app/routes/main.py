from flask import Blueprint, render_template, redirect, url_for, request, session, flash, jsonify
from app.models.department import Department
from app.models.user import Doctor

main_bp = Blueprint('main', __name__)

@main_bp.route('/login')
def login_redirect():
    return redirect(url_for('auth.login'))

@main_bp.route('/')
@main_bp.route('/index')
def index():
    # Load departments and doctors to display on landing page
    departments = Department.query.limit(6).all()
    doctors = Doctor.query.filter_by(availability_status='Available').limit(4).all()
    
    # Static stats
    stats = {
        'patients_served': '15,000+',
        'expert_doctors': Doctor.query.count() or '25',
        'departments_count': Department.query.count() or '10',
        'rooms_available': '85'
    }
    
    return render_template(
        'index.html', 
        departments=departments, 
        doctors=doctors,
        stats=stats
    )

@main_bp.route('/toggle-theme')
def toggle_theme():
    # Toggle theme in session between light and dark
    current_theme = session.get('theme', 'light')
    session['theme'] = 'dark' if current_theme == 'light' else 'light'
    
    # Redirect back to referring page or index
    ref = request.referrer or url_for('main.index')
    return redirect(ref)

@main_bp.route('/contact', methods=['POST'])
def contact():
    name = request.form.get('name')
    email = request.form.get('email')
    subject = request.form.get('subject')
    message = request.form.get('message')
    
    # We can process this contact request (e.g. log it or save to a file/DB)
    # For now, just flash a success message.
    flash("Thank you for reaching out! We have received your query and will contact you shortly.", "success")
    return redirect(url_for('main.index'))

@main_bp.route('/verify-report/<int:test_id>')
def verify_report(test_id):
    from app.models.lab_test import LabTest
    lab_test = LabTest.query.get_or_404(test_id)
    
    if request.args.get('json') == '1':
        results_data = []
        for r in lab_test.results:
            results_data.append({
                'param_name': r.template.test_name,
                'value': r.observed_value,
                'status': r.result_status,
                'range': r.normal_range_used,
                'unit': r.unit_used
            })
        return jsonify({
            'test_name': lab_test.test_name,
            'result_date': lab_test.result_date.strftime('%d-%b-%Y %H:%M') if lab_test.result_date else 'N/A',
            'is_critical': lab_test.is_critical,
            'results': results_data
        })
        
    return render_template('verify_report.html', lab_test=lab_test)

