from datetime import datetime
from app.models import db

class Department(db.Model):
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon_name = db.Column(db.String(50), default='bi-hospital') # Bootstrap icon class
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    doctors = db.relationship('Doctor', backref='department', lazy=True)

    def __repr__(self):
        return f"<Department {self.name}>"
