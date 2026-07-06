from app.models import db

class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(50), unique=True, nullable=False)
    setting_value = db.Column(db.String(255), nullable=False)
    
    def __repr__(self):
        return f"<SystemSetting {self.setting_key}: {self.setting_value}>"
