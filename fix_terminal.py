"""Restore incorrectly RETIRED TERMINAL assets"""
import requests

login_resp = requests.post('http://127.0.0.1:8000/api/v1/auth/login', json={'username': 'admin', 'password': 'admin123'}, timeout=10)
token = login_resp.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

r = requests.get('http://127.0.0.1:8000/api/v1/assets/', params={'page': 1, 'page_size': 200}, headers=headers, timeout=10)
items = r.json().get('data', {}).get('items', [])

# Find RETIRED TERMINAL assets
retired = [i for i in items if i.get('status') == 'RETIRED']
print(f'RETIRED assets ({len(retired)}):')
for i in retired:
    print(f"  id={i['id']}, ip={i['ip_address']}, type={i.get('asset_type', '')}, source={i['source']}, sync={i['sync_status']}")

# Restore TERMINAL assets that were incorrectly retired
for i in retired:
    if i.get('asset_type') == 'TERMINAL':
        update_resp = requests.put(
            f"http://127.0.0.1:8000/api/v1/assets/{i['id']}",
            json={'status': 'ACTIVE', 'sync_status': 'SYNCED'},
            headers=headers,
            timeout=10
        )
        print(f"  Restored id={i['id']}: {update_resp.status_code}")
