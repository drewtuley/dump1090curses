import requests
import sys

start=1
if len(sys.argv) > 1:
    start = int(sys.argv[1])
x=start
while x < start+1000:
    url = 'http://localhost:5000/search?icao_code=400{0:03X}'.format(x)
    print(url)
    response = requests.get(url)
    if response.status_code == 200:
        print(response.text)
    x += 1
