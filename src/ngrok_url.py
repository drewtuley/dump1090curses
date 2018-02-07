import requests

url = 'na'
r = requests.get('http://localhost:4040/api/tunnels')
if r.status_code == 200:
    if 'tunnels' in r.json():
        tunnels = r.json()['tunnels']
        for t in tunnels:
            if 'public_url' in t:
                url = t['public_url']

print(url)
