# MediCare - Hospital Management System

MediCare is a production-ready, fully functional full-stack web application designed for hospitals to manage clinical operations, patient registrations, appointments scheduling, doctor prescriptions, billing invoices, and analytical reports.

The application features a modern, responsive user interface with complete Role-Based Access Control (RBAC) and support for a Light/Dark theme.

---

## Technical Stack
- **Frontend**: HTML5, CSS3, Bootstrap 5, Javascript, Chart.js (Dashboards)
- **Backend**: Python Flask
- **ORM & Database**: SQLAlchemy, MySQL (with Pure Python PyMySQL driver)
- **Authentication**: Flask-Login, Werkzeug (Password Hashing), Session-based Auth
- **Reporting**: ReportLab (PDF generation), Pandas & OpenPyXL (Excel/CSV compiled exports)
- **Forms & Validation**: Flask-WTF, WTForms, Email-Validator

---

## Directory Structure
```
Hospital Management System/
├── run.py                       # App Entry Point (Starts server & Auto-seeds data)
├── config.py                    # Flask Configuration (MySQL URI, SQLite fallbacks)
├── requirements.txt             # Python Package Dependencies
├── schema.sql                   # Raw MySQL DDL database schema
├── init_db.py                   # Seeder Script (Initializes tables & mocks data)
└── app/                         # Main Application Package
    ├── __init__.py              # App Factory and Extensions setup
    ├── models/                  # SQLAlchemy ORM Models
    ├── forms/                   # WTForms validation schemes
    ├── routes/                  # Controller Blueprints (RBAC endpoints)
    ├── services/                # Business logic services (Billing, PDF, Excel)
    ├── static/                  # Static Assets (Style, JS, uploads)
    └── templates/               # Jinja2 HTML layouts
```

---

## Quick Setup Instructions

### 1. Prerequisites
Ensure **Python 3.10+** is installed on your computer.

### 2. Installation
Open a command prompt/terminal in the project root directory and run:

```bash
# Install dependencies
pip install -r requirements.txt
```

### 3. Run the Application
Start the Flask server by executing:

```bash
python run.py
```

> [!NOTE]
> On startup, `run.py` will automatically test the database connection.
> - If a local MySQL server is configured and running, it will create tables inside MySQL.
> - **SQLite Fallback**: If MySQL is unreachable, it will automatically fall back and create a local SQLite database (`medicare.db`). This makes the app **immediately runnable out-of-the-box** without any database configuration overhead!

Open your browser and navigate to: `http://localhost:5000`

---

## User Roles & Login Credentials

The seeder initializes the system with a clean Admin account. No mock doctor, receptionist, or patient accounts are pre-seeded, allowing you to test clinical records using real data:

| Role | Email Address | Password | Features |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@hospital.com` | `admin123` | Doctor/Staff/Room CRUD, System Settings, Analytics, Audit Logs |
| **Doctor / Receptionist** | *Registered by Admin* | *Set during registration* | Respective workflow dashboards |
| **Patient** | *Registered by Front Desk or Sign Up* | *Set during signup* | Patient scheduling & history dashboard |

---

## Database Configuration (MySQL)

By default, the application connects to a local MySQL server using:
- **Host**: `localhost:3306`
- **Database Name**: `medicare_db`
- **User**: `root`
- **Password**: `""` (Empty password)

To customize the MySQL connection credentials, you can configure these environment variables before starting the server:
- `DB_USER`: Your MySQL username (default: `root`)
- `DB_PASSWORD`: Your MySQL password (default: `""`)
- `DB_HOST`: Your MySQL host address (default: `localhost`)
- `DB_PORT`: Your MySQL port (default: `3306`)
- `DB_NAME`: Your MySQL database name (default: `medicare_db`)
- `SECRET_KEY`: Custom Flask secret key

Alternatively, set the complete connection URL using `DATABASE_URL` environment variable:
```bash
set DATABASE_URL=mysql+pymysql://username:password@host:port/database_name
```
