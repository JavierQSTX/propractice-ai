import requests
import json
from dotenv import load_dotenv
import os

load_dotenv(override=True)

# url = "https://my-fastapi-service-140249299005.us-central1.run.app"
url = "http://0.0.0.0:8080"
login_url = f"{url}/login"
feedback_url = f"{url}/feedback"
judge_url = f"{url}/judge"

body = {
    "username": os.environ["LOGIN_USERNAME"],
    "password": os.environ["LOGIN_PASSWORD"],
}
response = requests.post(login_url, json=body)

bearer_token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {bearer_token}"}

# VIDEO_FILENAME = "module_1/NAO_Module_2_Ethics,_Products_and_Services_(SUMMARY)_Overdraft_Protection_Scoring_Page - bad.webm"
# VIDEO_FILENAME = "module_1/NAO_Module_2_Ethics,_Products_and_Services_(SUMMARY)_Overdraft_Protection_Scoring_Page - good.webm"
# VIDEO_FILENAME = "module_1/NAO_Module_2_Ethics,_Products_and_Services_(SUMMARY)_Overdraft_Protection_Scoring_Page - Use Other Words.webm"

# feedback_input = {
#     "challenge": "2",
#     "question": "Why does a customer with checking need overdraft protection service?",
#     "briefing": "Customer may surface one or more general concerns during conversations. This ProPractice module focuses on the six most common general concerns and the proven best practice responses for products and services to maximize customer needs met. Overdraft Protection Service, On-line and Mobile Banking, Debit Card, Savings, Credit Card, Plus Package",
#     "keyElements": [
#         {
#             "script": "So they avoid any embarrassment, expense, and inconvenience",
#             "keywords": ["avoid", "embarrassment, expense, and inconvenience"],
#         },
#         {
#             "script": "In the unlikely event there are not enough funds in their account to cover a check they've written.",
#             "keywords": ["unlikely event", "not", "funds", "to cover", "check"],
#         },
#         {
#             "script": "There is no fee to establish this service.",
#             "keywords": ["no fee to establish"],
#         },
#     ],
# }


VIDEO_FILENAME = "video_68c9b75d32d44.mp4"
# VIDEO_FILENAME = "module_2/challenge 3 good recroding.mp4"
# VIDEO_FILENAME = "module_2/Challenge 3 Synonyms.mp4"


feedback_input = {
    "challenge": "3",
    "question": "Check Balance in Account",
    "briefing": "In this module you will learn what to say when hearing a variety of clues.● Rate inquiry  ● Check Balance in Account ● High balance in savings ● CD maturing in the next month",
    "keyElements": [
        {
            "script": " Yes, I am happy to check the balance for you. ",
            "keywords": ["Yes,", "happy", "check", "balance"],
        },
        {
            "script": " But I want to ensure you know that there are other easy ways to check your balance ",
            "keywords": ["other easy ways", "check", "balance"],
        },
        {
            "script": " In addition to using our ATM, you are also able to check your balance, ",
            "keywords": ["addition", "ATM,", "check", "balance,"],
        },
        {
            "script": " Anytime, and virtually anywhere through our convenient online banking, and mobile banking. ",
            "keywords": [
                "Anytime,",
                "anywhere through",
                "convenient on",
                "line",
                ",",
                "mobile banking",
            ],
        },
        {
            "script": " I'd like to help you with this now if you would like to get started.",
            "keywords": ["help", "now"],
        },
    ],
    "user_id": "LID--fff108e0b0682e0d2e0108a875739904",
    "tags": ["Check Balance in Account", "Perfect Hour for Operations"],
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
print(response.json()["accuracy"])
print(response.json()["confidence"])

# data = {
#     "session_id": "77bac4f8-e28a-45a6-9254-9a18902914b5",
#     "positive_feedback": False,
# }

# judge_url = f"{url}/like"
# response = requests.post(judge_url, json=data, headers=headers)

# from pprint import pprint

# pprint(response.json())
