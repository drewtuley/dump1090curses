import requests
import re


r = requests.get('http://ip4.me')
if r.status_code == 200:
    m=re.search('\d+[.]\d+[.]\d+[.]\d+', r.text)
    if m != None:
        print (m.group())
