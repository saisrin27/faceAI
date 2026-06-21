from backend.database.db import get_db

def log_audit_action(admin_id: int, action: str, target_user_id: int = None):
    """Log administrative actions for security tracking."""
    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO audit_logs (admin_id, action, target_user_id) VALUES (%s, %s, %s)",
                    (admin_id, action, target_user_id)
                )
    except Exception as e:
        # We don't block operations if audit logging fails, but we print/log the error.
        print(f"Error writing audit log: {e}")
