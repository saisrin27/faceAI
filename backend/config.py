import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(BASE_DIR / ".env")

# Database configurations
DB_HOST = os.getenv("FACEAI_DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("FACEAI_DB_PORT", "3306"))
DB_USER = os.getenv("FACEAI_DB_USER", "root")
DB_PASSWORD = os.getenv("FACEAI_DB_PASSWORD", "")
DB_NAME = os.getenv("FACEAI_DB_NAME", "sbsteqgf_faceai")

# Upload and Storage directories
UPLOAD_DIR = BASE_DIR / "uploads"
USERS_DIR = UPLOAD_DIR / "users"
ADMINS_DIR = UPLOAD_DIR / "admins"
REGISTERED_DIR = UPLOAD_DIR / "registered"
ATTENDANCE_LOGS_DIR = UPLOAD_DIR / "attendance_logs"

# Ensure directories exist
for folder in [UPLOAD_DIR, USERS_DIR, ADMINS_DIR, REGISTERED_DIR, ATTENDANCE_LOGS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# Face Recognition parameters
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

YOLO_FACE_MODEL_FILE = DATA_DIR / "yolov8n-face-lindevs.pt"
RECOGNIZER_FILE = DATA_DIR / "face_model.yml"

# Security & Session Settings
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key-faceai-attendance-system-2026")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
CAPTCHA_EXPIRE_MINUTES = 3
COSINE_SIMILARITY_THRESHOLD = 0.55  # Cosine similarity threshold for InsightFace ArcFace face matching (higher is better)
