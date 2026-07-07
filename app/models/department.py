from datetime import datetime
from app.models import db

class Department(db.Model):
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon_name = db.Column(db.String(50), default='bi-hospital') # Bootstrap icon class
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Unique constraint per hospital
    __table_args__ = (
        db.UniqueConstraint('hospital_id', 'name', name='unique_hospital_department'),
    )

    # Relationships
    doctors = db.relationship('Doctor', backref='department', lazy=True)

    def __repr__(self):
        return f"<Department {self.name}>"
