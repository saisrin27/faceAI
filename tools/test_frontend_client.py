import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from frontend.utils.api_client import FaceAiApiClient

c = FaceAiApiClient()
print('Base URL:', c.base_url)
# login and call overview
try:
    data = c.login('admin@faceai.com','admin123')
    print('Login ok')
    ov = c.get_attendance_overview_stats()
    print('Overview OK, keys:', list(ov.keys()))
except Exception as e:
    print('ERROR', e)
