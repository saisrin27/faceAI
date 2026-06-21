import requests

LOGIN_URL = 'http://127.0.0.1:8003/auth/login'
OV_URL = 'http://127.0.0.1:8003/admin/attendance-overview'

r = requests.post(LOGIN_URL, json={'email':'admin@faceai.com','password':'admin123'}, timeout=10)
print('LOGIN', r.status_code)
print('LOGIN headers:', r.headers)
print('LOGIN text:', r.text)
if r.status_code == 200:
    token = r.json().get('access_token')
    headers = {'Authorization': f'Bearer {token}'}
    r2 = requests.get(OV_URL, headers=headers, timeout=20)
    print('\nOVERVIEW', r2.status_code)
    print('Content-Type:', r2.headers.get('Content-Type'))
    print('Headers:', r2.headers)
    try:
        print('JSON:', r2.json())
    except Exception as e:
        print('Text:', r2.text)
        print('JSON parse error:', e)
else:
    print('Login failed')
