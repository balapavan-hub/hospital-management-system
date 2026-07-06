from datetime import date
from app.models.appointment import Appointment
from app.models.user import Doctor

class AppointmentService:
    @staticmethod
    def is_slot_available(doctor_id, appointment_date, time_slot, exclude_appointment_id=None):
        """
        Check if a doctor is available for a specific date and time slot.
        """
        # First check if the doctor exists and is 'Available'
        doctor = Doctor.query.get(doctor_id)
        if not doctor or doctor.availability_status != 'Available':
            return False
            
        # Check if there's any active appointment for this doctor, date and slot
        query = Appointment.query.filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == appointment_date,
            Appointment.time_slot == time_slot,
            Appointment.status.in_(['Pending', 'Confirmed', 'Completed'])
        )
        
        if exclude_appointment_id:
            query = query.filter(Appointment.id != exclude_appointment_id)
            
        existing_appt = query.first()
        return existing_appt is None

    @staticmethod
    def get_booked_slots(doctor_id, appointment_date):
        """
        Retrieve a list of time slots already booked for a doctor on a specific date.
        """
        appointments = Appointment.query.filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == appointment_date,
            Appointment.status.in_(['Pending', 'Confirmed', 'Completed'])
        ).all()
        
        return [appt.time_slot for appt in appointments]
