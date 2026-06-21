import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend import config
import pymysql

conn = pymysql.connect(host=config.DB_HOST, port=config.DB_PORT, user=config.DB_USER, password=config.DB_PASSWORD, database=config.DB_NAME, charset='utf8mb4', autocommit=True)
try:
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, role, approval_status FROM users WHERE email = %s", ('admin@faceai.com',))
        row = cursor.fetchone()
        print('Before:', row)
        cursor.execute("UPDATE users SET role = 'Admin', approval_status = 'Approved' WHERE email = %s", ('admin@faceai.com',))
        cursor.execute("SELECT id, role, approval_status FROM users WHERE email = %s", ('admin@faceai.com',))
        print('After:', cursor.fetchone())
finally:
    conn.close()
