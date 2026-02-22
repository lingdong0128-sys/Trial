import requests
import sys

url = "http://db574449-985d-4416-8e95-aa83c02d8078.node5.buuoj.cn:81/"
try:
    response = requests.get(url, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print("\n" + "="*50 + "\n")
    print("Response Body:")
    print(response.text[:2000])
except Exception as e:
    print(f"Error: {e}")