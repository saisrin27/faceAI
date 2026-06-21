import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
import logging
from backend import config


logger = logging.getLogger("faceai.database")

def get_db_connection():
    """Establish and return a new connection to the MySQL database."""
    try:
        return pymysql.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            charset="utf8mb4",
            cursorclass=DictCursor,
            autocommit=True
        )
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

@contextmanager
def get_db():
    """Context manager to yield a db connection and ensure it closes after usage."""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Ensure database schema is initialized correctly."""
    try:
        # Connect to MySQL server without database first to ensure database exists
        temp_conn = pymysql.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            charset="utf8mb4",
            autocommit=True
        )
        with temp_conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {config.DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        temp_conn.close()

        # Connect to the database and set up tables
        with get_db() as conn:
            with conn.cursor() as cursor:
                # 1. Users
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(150) NOT NULL,
                    email VARCHAR(191) NOT NULL UNIQUE,
                    phone_number VARCHAR(30) NOT NULL,
                    department VARCHAR(100) NULL,
                    password VARCHAR(255) NOT NULL,
                    role ENUM('Admin', 'User', 'Registered') NOT NULL DEFAULT 'Registered',
                    approval_status ENUM('Pending', 'Approved', 'Rejected') NOT NULL DEFAULT 'Pending',
                    profile_image VARCHAR(255) NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_face_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_email (email)
                );
                """)
                
                # Run migration to add last_face_update if it doesn't exist
                try:
                    cursor.execute("SELECT last_face_update FROM users LIMIT 1")
                except Exception:
                    cursor.execute("ALTER TABLE users ADD COLUMN last_face_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                
                # Run migration to add department if it doesn't exist
                try:
                    cursor.execute("SELECT department FROM users LIMIT 1")
                except Exception:
                    cursor.execute("ALTER TABLE users ADD COLUMN department VARCHAR(100) NULL AFTER phone_number")
                
                # 2. Face Embeddings
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS face_embeddings (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    embedding_path VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                """)
                
                # 3. Attendance
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance (
                    attendance_id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    attendance_date DATE NOT NULL,
                    check_in_time DATETIME NOT NULL,
                    check_out_time DATETIME NULL,
                    status VARCHAR(50) NOT NULL DEFAULT 'Present',
                    image_path VARCHAR(255) NULL,
                    confidence FLOAT NULL,
                    half_day BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE KEY unique_user_daily_attendance (user_id, attendance_date)
                );
                """)
                
                # Run migration to add confidence if it doesn't exist
                try:
                    cursor.execute("SELECT confidence FROM attendance LIMIT 1")
                except Exception:
                    cursor.execute("ALTER TABLE attendance ADD COLUMN confidence FLOAT NULL")
                
                # Run migration to add half_day if it doesn't exist
                try:
                    cursor.execute("SELECT half_day FROM attendance LIMIT 1")
                except Exception:
                    cursor.execute("ALTER TABLE attendance ADD COLUMN half_day BOOLEAN DEFAULT FALSE")
                
                # 4. Attendance Logs
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NULL,
                    action VARCHAR(255) NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    image_path VARCHAR(255) NULL
                );
                """)
                # Drop captcha_verifications table if it doesn't match the expected schema (e.g., missing captcha_key)
                try:
                    cursor.execute("SELECT captcha_key FROM captcha_verifications LIMIT 1")
                except Exception:
                    cursor.execute("DROP TABLE IF EXISTS captcha_verifications")
                
                # 5. Captcha Verifications
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS captcha_verifications (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    captcha_key VARCHAR(191) NOT NULL UNIQUE,
                    captcha_value VARCHAR(10) NOT NULL,
                    expires_at TIMESTAMP NOT NULL
                );
                """)
                
                # 6. Audit Logs
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    admin_id INT NOT NULL,
                    action VARCHAR(255) NOT NULL,
                    target_user_id INT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE
                );
                """)

                # 7. Comments
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS comments (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NULL,
                    user_name VARCHAR(150) NOT NULL,
                    comment_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """)
                # If users table exists, ensure a foreign key relationship (user_id -> users.id)
                try:
                    cursor.execute(
                        "SELECT 1 FROM information_schema.KEY_COLUMN_USAGE "
                        "WHERE TABLE_SCHEMA=%s AND TABLE_NAME='comments' "
                        "AND COLUMN_NAME='user_id' AND REFERENCED_TABLE_NAME='users' LIMIT 1",
                        (config.DB_NAME,)
                    )
                    if not cursor.fetchone():
                        # Add FK constraint to keep referential integrity; use SET NULL on delete
                        try:
                            cursor.execute(
                                "ALTER TABLE comments ADD CONSTRAINT fk_comments_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL"
                            )
                        except Exception:
                            # ignore failures here (older MySQL, missing privileges, etc.)
                            pass
                except Exception:
                    # best-effort, do not fail init if metadata read is unavailable
                    pass

                # 8. Attendance Settings (office hours + grace period configured by Admin)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance_settings (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    start_time TIME NOT NULL DEFAULT '09:00:00',
                    end_time TIME NOT NULL DEFAULT '18:00:00',
                    grace_period_minutes INT NOT NULL DEFAULT 30,
                    updated_by INT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL
                );
                """)

                # Older installs may have a partial attendance_settings table.
                for column_name, ddl in (
                    ("updated_by", "ALTER TABLE attendance_settings ADD COLUMN updated_by INT NULL"),
                    ("updated_at", "ALTER TABLE attendance_settings ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                ):
                    try:
                        cursor.execute(f"SELECT {column_name} FROM attendance_settings LIMIT 1")
                    except Exception:
                        cursor.execute(ddl)

                # Seed default attendance settings row (id=1) if none exists
                cursor.execute("SELECT id FROM attendance_settings LIMIT 1")
                if not cursor.fetchone():
                    cursor.execute("""
                    INSERT INTO attendance_settings (start_time, end_time, grace_period_minutes)
                    VALUES ('09:00:00', '18:00:00', 30)
                    """)
                    logger.info("Default attendance settings seeded (09:00–18:00, 30 min grace).")

                # 9. System Detection Logs (for animal/weapon/object detections)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_detection_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    detection_type VARCHAR(50) NOT NULL,
                    object_label VARCHAR(100) NOT NULL,
                    confidence FLOAT DEFAULT 0.0,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    camera_id INT DEFAULT 1,
                    is_warning BOOLEAN DEFAULT FALSE,
                    INDEX idx_timestamp (timestamp),
                    INDEX idx_detection_type (detection_type)
                );
                """)
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
