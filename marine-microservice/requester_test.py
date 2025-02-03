import requests

url = "http://localhost:8000/compare-videos"

files = {
    'video1': open(r'C:\Users\ASUS\Desktop\Side Quest Final\marine\marine-microservice\test_vid1.mp4', 'rb'),
    'video2': open(r'C:\Users\ASUS\Desktop\Side Quest Final\marine\marine-microservice\test_vid4.mp4', 'rb')
}

response = requests.post(url, files=files)

print(response.json())
