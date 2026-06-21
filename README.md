# Face AI Attendance System

A professional, modularized Streamlit application for AI-powered face recognition attendance tracking.

## Features
- **Face Recognition**: Powered by OpenCV Haar Cascades for real-time detection and verification.
- **MySQL Backend**: Secure storage for user profiles, face templates, and attendance logs.
- **Role-Based Access**: Specialized dashboards for Admins and regular Users.
- **Modular Structure**: Production-ready folder organization for scalability.
- **Premium UI**: Modern dark-mode aesthetic with custom CSS.

## Project Structure
```
FaceAI_Attendance_System/
├── app.py                # Main entry point
├── config/               # Settings and Constants
├── database/             # Connection and SQL Queries
├── modules/              # Core Logic (Auth, Face Rec, etc.)
├── pages/                # UI Components
├── assets/               # CSS and Static Images
└── .streamlit/           # Secret configurations
```

## Setup Instructions
1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`.
3. Configure your MySQL database in `.streamlit/secrets.toml`.
4. Run the app: `streamlit run app.py`.

## Technology Stack
- **Frontend**: Streamlit
- **Computer Vision**: OpenCV
- **Database**: MySQL
- **Language**: Python 3.x
