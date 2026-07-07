from app.models import db
from app.models.lab_test import LabTest, LabTestResult
from app.services.notification_service import NotificationService
from app.models.user import Doctor, User

class AlertService:
    @staticmethod
    def check_result_limits(result):
        """
        Compare observed value with template normal and critical limits.
        Returns: 'Normal', 'Low', 'High', 'Critical'
        """
        template = result.template
        if not template:
            return 'Normal'
            
        val_str = result.observed_value
        
        # Attempt to parse as float
        try:
            # Handle fraction or range (e.g. 120/80 for Blood Pressure)
            if '/' in val_str:
                parts = val_str.split('/')
                systolic = float(parts[0].strip())
                diastolic = float(parts[1].strip())
                
                # Normal is Systolic <= 120, Diastolic <= 80
                # Critical is Systolic >= 180 or Diastolic >= 120
                if systolic >= 180 or diastolic >= 120:
                    return 'Critical'
                elif systolic > 120 or diastolic > 80:
                    return 'High'
                return 'Normal'

            val = float(val_str)
        except ValueError:
            # Non-numeric observed value (e.g. "Positive" / "Negative")
            if template.normal_range_text:
                if val_str.strip().lower() == template.normal_range_text.strip().lower():
                    return 'Normal'
                # If observed positive but normal is negative, trigger critical
                if 'neg' in template.normal_range_text.lower() and 'pos' in val_str.lower():
                    return 'Critical'
            return 'Normal'

        # Check critical ranges first
        if template.critical_range_min is not None and val <= template.critical_range_min:
            return 'Critical'
        if template.critical_range_max is not None and val >= template.critical_range_max:
            return 'Critical'

        # Check normal ranges
        if template.normal_range_min is not None and val < template.normal_range_min:
            return 'Low'
        if template.normal_range_max is not None and val > template.normal_range_max:
            return 'High'

        return 'Normal'

    @staticmethod
    def process_lab_test_alerts(lab_test):
        """
        Scan all results for a lab test. If any are critical, mark lab_test as critical
        and send notifications to Admin and consulting Doctor.
        """
        has_critical = False
        for result in lab_test.results:
            status = AlertService.check_result_limits(result)
            result.result_status = status
            if status == 'Critical':
                has_critical = True
        
        lab_test.is_critical = has_critical
        db.session.commit()
        
        if has_critical:
            # 1. Notify consulting Doctor
            if lab_test.doctor:
                NotificationService.create_notification(
                    user_id=lab_test.doctor.user_id,
                    title="CRITICAL LAB ALERT",
                    message=f"Critical results observed for Patient {lab_test.patient.full_name} on test {lab_test.test_name} (Sample ID: {lab_test.sample_id})."
                )
            
            # 2. Notify Admins
            admins = User.query.filter_by(role='Admin').all()
            for admin in admins:
                NotificationService.create_notification(
                    user_id=admin.id,
                    title="CRITICAL LAB ALERT",
                    message=f"Critical result detected in Lab Test #{lab_test.id} ({lab_test.test_name}) for Patient {lab_test.patient.full_name}."
                )
                
            # Log critical alert to SMS Mock
            from app.services.communication_service import CommunicationService
            doctor_phone = lab_test.doctor.phone if lab_test.doctor else "9876543210"
            CommunicationService.send_mock_sms(
                to_phone=doctor_phone,
                message=f"[CRITICAL ALERT] Patient {lab_test.patient.full_name} has critical lab results for {lab_test.test_name}."
            )
            
        return has_critical
