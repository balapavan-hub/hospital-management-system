from flask import request
from app.models import db
from app.models.audit_log import AuditLog

class AuditService:
    @staticmethod
    def log_action(user_id, action, ip_address=None, hospital_id=None):
        """
        Record a user action inside the audit logs.
        """
        # Fallback to flask request IP if not explicitly provided
        if not ip_address:
            try:
                ip_address = request.remote_addr
            except RuntimeError:
                # Outside request context (e.g. CLI/scripts)
                ip_address = '127.0.0.1'

        # Auto-detect hospital_id from current_user if not explicitly passed
        if not hospital_id:
            from flask_login import current_user
            if current_user and hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                hospital_id = getattr(current_user, 'hospital_id', None)
                
        log = AuditLog(
            user_id=user_id,
            action=action,
            ip_address=ip_address,
            hospital_id=hospital_id
        )
        db.session.add(log)
        db.session.commit()
        return log

    @staticmethod
    def get_logs(limit=100, offset=0):
        """
        Retrieve audit logs with pagination.
        """
        return AuditLog.query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
