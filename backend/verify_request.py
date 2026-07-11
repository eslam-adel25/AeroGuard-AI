import urllib.request, urllib.error
req = urllib.request.Request('http://127.0.0.1:8000/api/v1/auth/verify?token=oASqTbGqhmnOdhSTZmOack1kR7y8jAlAoEL9FfEvg7w', method='GET')
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        print(resp.status)
        print(resp.read().decode())
except urllib.error.HTTPError as e:
    print(e.code)
    print(e.read().decode())
