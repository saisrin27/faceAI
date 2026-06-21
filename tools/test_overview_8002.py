import requests

LOGIN_URL = 'http://127.0.0.1:8002/auth/login'
OV_URL = 'http://127.0.0.1:8002/admin/attendance-overview'

try:
    r = requests.post(LOGIN_URL, json={'email':'admin@faceai.com','password':'admin123'}, timeout=10)
    print('LOGIN', r.status_code)
    print(r.text)
    if r.status_code == 200:
        token = r.json().get('access_token')
        headers = {'Authorization': f'Bearer {token}'}
        r2 = requests.get(OV_URL, headers=headers, timeout=20)
        print('\nOVERVIEW', r2.status_code)
        print(r2.text)
except Exception as e:
    print('ERROR', e)
