from app.models import db
from app.models.notification import Notification

class NotificationService:
    @staticmethod
    def create_notification(user_id, title, message):
        """
        Create a new notification for a specific user.
        """
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message
        )
        db.session.add(notification)
        db.session.commit()
        return notification

    @staticmethod
    def get_unread_notifications(user_id):
        """
        Get all unread notifications for a user.
        """
        return Notification.query.filter_by(user_id=user_id, is_read=False).order_by(Notification.created_at.desc()).all()

    @staticmethod
    def mark_as_read(notification_id):
        """
        Mark a notification as read.
        """
        notification = Notification.query.get(notification_id)
        if notification:
            notification.is_read = True
            db.session.commit()
            return True
        return False

    @staticmethod
    def mark_all_as_read(user_id):
        """
        Mark all notifications for a user as read.
        """
        Notification.query.filter_by(user_id=user_id, is_read=False).update({Notification.is_read: True})
        db.session.commit()
        return True
