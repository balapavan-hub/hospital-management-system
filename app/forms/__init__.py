from app.forms.auth_forms import (
    LoginForm, PatientRegisterForm, ForgotPasswordForm, 
    ResetPasswordForm, UpdateProfileForm, ChangePasswordForm, HospitalRegisterForm
)
from app.forms.admin_forms import DoctorForm, ReceptionistForm, DepartmentForm, RoomForm, LabTechnicianForm, NurseForm, PharmacistForm, BillingExecutiveForm
from app.forms.patient_forms import BookAppointmentForm, RescheduleAppointmentForm
from app.forms.doctor_forms import PrescriptionForm, MedicalReportForm
from app.forms.receptionist_forms import QuickRegisterPatientForm, GenerateBillForm
from app.forms.lab_test_forms import (
    DoctorOrderLabForm, LabPackageForm, LabTestTemplateForm, 
    InventoryItemForm, RecordLabResultsForm
)
