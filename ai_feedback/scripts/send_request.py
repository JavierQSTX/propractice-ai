import requests
import json
from dotenv import load_dotenv
import os

load_dotenv(override=True)

# url = "https://my-fastapi-service-140249299005.us-central1.run.app"
url = "http://0.0.0.0:8080"
login_url = f"{url}/login"
feedback_url = f"{url}/feedback"

body = {
    "username": os.environ["LOGIN_USERNAME"],
    "password": os.environ["LOGIN_PASSWORD"],
}
response = requests.post(login_url, json=body)

bearer_token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {bearer_token}"}

# VIDEO_FILENAME = "second recoding with errors.mp4"
# SCRIPT_FILENAME = "Script.pdf"

# VIDEO_FILENAME = "NAO_Module_2_Ethics,_Products_and_Services_(SUMMARY)_Overdraft_Protection_Scoring_Page - bad.webm"
# VIDEO_FILENAME = "NAO_Module_2_Ethics,_Products_and_Services_(SUMMARY)_Overdraft_Protection_Scoring_Page - good.webm"
VIDEO_FILENAME = "NAO_Module_2_Ethics,_Products_and_Services_(SUMMARY)_Overdraft_Protection_Scoring_Page - Use Other Words.webm"

feedback_input = {
    "challenge": "2",
    "question": "Why does a customer with checking need overdraft protection service?",
    "briefing": "Customer may surface one or more general concerns during conversations. This ProPractice module focuses on the six most common general concerns and the proven best practice responses for products and services to maximize customer needs met. Overdraft Protection Service, On-line and Mobile Banking, Debit Card, Savings, Credit Card, Plus Package",
    "keyElements": [
        {
            "script": "So they avoid any embarrassment, expense, and inconvenience",
            "keywords": ["avoid", "embarrassment, expense, and inconvenience"],
        },
        {
            "script": "In the unlikely event there are not enough funds in their account to cover a check they've written.",
            "keywords": ["unlikely event", "not", "funds", "to cover", "check"],
        },
        {
            "script": "There is no fee to establish this service.",
            "keywords": ["no fee to establish"],
        },
    ],
}

files = {
    "video": (
        "video.mp4",
        open(f"./data/{VIDEO_FILENAME}", "rb"),
        "video/mp4",
    ),
}
data = {"feedback_input_str": json.dumps(feedback_input)}

response = requests.post(feedback_url, files=files, data=data, headers=headers)
print(response.json()["feedback"])
