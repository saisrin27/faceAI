import requests
import logging

logger = logging.getLogger("faceai.api_client")

class FaceAiApiClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.token = None
        
    def set_token(self, token: str):
        self.token = token
        
    def clear_token(self):
        self.token = None
        
    def _get_headers(self, is_multipart=False) -> dict:
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _handle_error(self, r, default_msg: str):
        try:
            detail = r.json().get("detail", default_msg)
        except Exception:
            detail = f"Server error ({r.status_code}): {r.text[:120]}"
        raise Exception(detail)

    def check_health(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/health", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def get_captcha(self) -> dict:
        r = requests.get(f"{self.base_url}/captcha/get")
        if r.status_code == 200:
            return r.json()
        raise Exception(f"Failed to fetch CAPTCHA: {r.text}")

    def login(self, email: str, password: str) -> dict:
        payload = {"email": email, "password": password}
        r = requests.post(f"{self.base_url}/auth/login", json=payload)
        if r.status_code == 200:
            data = r.json()
            self.set_token(data["access_token"])
            return data
        self._handle_error(r, "Login failed.")

    def register(self, data: dict) -> dict:
        # Form-data post
        r = requests.post(f"{self.base_url}/auth/register", data=data)
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Registration failed.")

    def upload_enrollment_pose(self, user_id: int, pose: str, image_bytes: bytes) -> dict:
        files = {"image": ("frame.jpg", image_bytes, "image/jpeg")}
        data = {"user_id": str(user_id), "pose": pose}
        r = requests.post(f"{self.base_url}/enroll/upload-pose", data=data, files=files)
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, f"Pose {pose} upload failed.")

    def complete_enrollment(self, user_id: int) -> dict:
        data = {"user_id": str(user_id)}
        r = requests.post(f"{self.base_url}/enroll/complete", data=data)
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to complete face enrollment.")

    def scan_attendance_face(self, image_bytes: bytes) -> dict:
        files = {"image": ("scan.jpg", image_bytes, "image/jpeg")}
        r = requests.post(f"{self.base_url}/attendance/scan", files=files)
        if r.status_code == 200:
            return r.json()
        raise Exception("Failed to contact attendance server.")

    def check_out(self, user_id: int) -> dict:
        r = requests.post(f"{self.base_url}/attendance/check-out", json={"user_id": user_id})
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Checkout failed.")

    # --- USER METRICS ---
    def get_user_dashboard_stats(self, user_id: int) -> dict:
        r = requests.get(f"{self.base_url}/user/dashboard-stats?user_id={user_id}")
        if r.status_code == 200:
            return r.json()
        raise Exception("Failed to fetch dashboard metrics.")

    def get_user_attendance_history(self, user_id: int) -> list:
        r = requests.get(f"{self.base_url}/user/attendance-history?user_id={user_id}")
        if r.status_code == 200:
            return r.json()
        raise Exception("Failed to fetch attendance history.")

    # --- ADMIN ACTIONS ---
    def get_admin_stats(self) -> dict:
        r = requests.get(f"{self.base_url}/admin/stats", headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        raise Exception("Failed to fetch admin stats.")

    def get_admin_users_list(self) -> list:
        r = requests.get(f"{self.base_url}/admin/users-list", headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        raise Exception("Failed to fetch user list.")

    def approve_user(self, user_id: int) -> dict:
        data = {"user_id": str(user_id)}
        r = requests.post(f"{self.base_url}/admin/approve-user", data=data, headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "User approval failed.")

    def reject_user(self, user_id: int) -> dict:
        data = {"user_id": str(user_id)}
        r = requests.post(f"{self.base_url}/admin/reject-user", data=data, headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "User rejection failed.")

    def modify_user_role(self, user_id: int, action: str) -> dict:
        payload = {"user_id": user_id, "action": action}
        r = requests.post(f"{self.base_url}/admin/modify-user-role", json=payload, headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Action failed.")

    def remove_user(self, user_id: int) -> dict:
        r = requests.delete(f"{self.base_url}/admin/remove-user/{user_id}", headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "User deletion failed.")

    def get_audit_logs(self) -> list:
        r = requests.get(f"{self.base_url}/admin/audit-logs", headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        raise Exception("Failed to fetch audit logs.")

    def update_password(self, user_id: int, password: str) -> dict:
        payload = {"user_id": user_id, "password": password}
        r = requests.post(f"{self.base_url}/auth/update-password", json=payload)
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Password update failed.")

    def get_admin_attendance_stats(self) -> dict:
        r = requests.get(f"{self.base_url}/admin/admin-attendance", headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        raise Exception("Failed to fetch admin attendance stats.")

    def get_attendance_overview_stats(self) -> dict:
        r = requests.get(f"{self.base_url}/admin/attendance-overview", headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        # Try to extract detailed error message from server response
        try:
            detail = r.json().get("detail")
            if detail:
                raise Exception(detail)
        except Exception:
            # Fall back to response text
            pass
        raise Exception(f"Failed to fetch attendance overview stats: {r.status_code} {r.text}")

    def get_attendance_graph_data(self, period: str = "This Week") -> dict:
        r = requests.get(f"{self.base_url}/api/attendance/graph?period={period}", headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        raise Exception(f"Failed to fetch attendance graph data: {r.status_code} {r.text}")

    def update_profile(self, user_id: int, name: str, email: str, phone_number: str, department: str = None, image_bytes: bytes = None) -> dict:
        data = {
            "user_id": str(user_id),
            "name": name,
            "email": email,
            "phone_number": phone_number,
            "department": department or ""
        }
        files = None
        if image_bytes:
            files = {"image": ("profile.jpg", image_bytes, "image/jpeg")}
            
        r = requests.post(f"{self.base_url}/user/update-profile", data=data, files=files, headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Profile update failed.")


    def get_attendance_report(self, date_str: str) -> list:
        r = requests.get(
            f"{self.base_url}/admin/attendance-report?date_str={date_str}",
            headers=self._get_headers()
        )
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to fetch attendance report.")

    # ── Comment methods ──────────────────────────────────────────────────────

    def get_comments(self) -> list:
        r = requests.get(f"{self.base_url}/comments")
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to load comments.")

    def post_comment(self, user_id, user_name: str, comment_text: str) -> dict:
        payload = {
            "user_id":      user_id,
            "user_name":    user_name,
            "comment_text": comment_text
        }
        r = requests.post(f"{self.base_url}/comments", json=payload)
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to post comment.")

    def delete_comment(self, comment_id: int) -> dict:
        r = requests.delete(
            f"{self.base_url}/comments/{comment_id}",
            headers=self._get_headers()
        )
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to delete comment.")

    # --- ATTENDANCE SETTINGS ---
    def get_attendance_settings(self) -> dict:
        """Fetch current attendance time settings (admin-only)."""
        r = requests.get(
            f"{self.base_url}/admin/attendance-settings",
            headers=self._get_headers()
        )
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to fetch attendance settings.")

    def save_attendance_settings(self, start_time: str, end_time: str, grace_period_minutes: int) -> dict:
        """Save attendance time settings (admin-only). start_time and end_time in 'HH:MM' format."""
        payload = {
            "start_time": start_time,
            "end_time": end_time,
            "grace_period_minutes": grace_period_minutes
        }
        r = requests.post(
            f"{self.base_url}/admin/attendance-settings",
            json=payload,
            headers=self._get_headers()
        )
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to save attendance settings.")

    def update_attendance_settings(self, start_time: str, end_time: str, grace_period_minutes: int) -> dict:
        """Update attendance time settings. Kept separate for callers that expect an update method."""
        payload = {
            "start_time": start_time,
            "end_time": end_time,
            "grace_period_minutes": grace_period_minutes
        }
        r = requests.put(
            f"{self.base_url}/admin/attendance-settings",
            json=payload,
            headers=self._get_headers()
        )
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to update attendance settings.")

    def delete_attendance_settings(self) -> dict:
        """Delete attendance settings (admin-only)."""
        r = requests.delete(
            f"{self.base_url}/admin/attendance-settings",
            headers=self._get_headers()
        )
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to delete attendance settings.")

    def rebuild_face_cache(self) -> dict:
        r = requests.post(f"{self.base_url}/admin/rebuild-face-cache", headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to rebuild face embeddings cache.")

    def override_attendance(self, user_id: int, date_str: str, check_in: str, check_out: str, status: str) -> dict:
        payload = {
            "user_id": user_id,
            "attendance_date": date_str,
            "check_in": check_in or None,
            "check_out": check_out or None,
            "status": status
        }
        r = requests.post(f"{self.base_url}/admin/attendance-override", json=payload, headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to override attendance.")

    def get_attendance_report_range(self, start_date: str, end_date: str) -> list:
        r = requests.get(
            f"{self.base_url}/admin/attendance-report-range?start_date_str={start_date}&end_date_str={end_date}",
            headers=self._get_headers()
        )
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to fetch bulk attendance report.")

    def get_public_stats(self) -> dict:
        r = requests.get(f"{self.base_url}/api/public/stats")
        if r.status_code == 200:
            return r.json()
        raise Exception("Failed to fetch public stats metrics.")

