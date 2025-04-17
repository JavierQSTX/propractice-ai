import requests
import subprocess

url = "https://my-fastapi-service-140249299005.us-central1.run.app/feedback"

bearer_token = (
    subprocess.check_output(["gcloud", "auth", "print-identity-token"]).decode().strip()
)

headers = {"Authorization": f"Bearer {bearer_token}"}

files = {
    "video": (
        "video.mp4",
        open("./data/second recoding with errors.mp4", "rb"),
        "video/mp4",
    ),
    "pdf": ("document.pdf", open("./data/Script.pdf", "rb"), "application/pdf"),
}

response = requests.post(url, files=files, headers=headers)
# print(response.status_code)
# print(response.json()["feedback"])
print(response.text)
