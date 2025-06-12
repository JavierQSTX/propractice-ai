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


VIDEO_FILENAME = "module_2/Challenge 3 bad recording.mp4"
# VIDEO_FILENAME = "module_2/challenge 3 good recroding.mp4"
# VIDEO_FILENAME = "module_2/Challenge 3 Synonyms.mp4"


feedback_input = {
    "challenge": 3,
    "tags": ["test1", "test2"],
    "user_id": "my_test_user_id",
    "question": "You are speaking with an existing Member. What should you say to transition into the Member Financial Review?",
    "briefing": "By learning and practicing with this ProPractice module, you will increase your confidence and success in presenting the Member with a compelling entry line when you are seeking to conduct a Member Review. • Transitioning After the Use of a Tag-On • New Member Entry Line • Existing Member Entry Line • Transitioning to the Member Financial Review After Problem Resolution",
    "keyElements": [
        {
            "script": "Thank you for being a River City Federal Credit Union Member , we appreciate the opportunity to serve you.",
            "keywords": ["Thank you"],
        },
        {
            "script": "It's my responsibility to help Members achieve their financial goals and make their banking more convenient",
            "keywords": [
                "My responsability",
                "help Members achieve",
                "financial goals",
                "make banking",
                "convenient",
            ],
        },
        {
            "script": "Circumstances for our Members typically change over time, and we are implementing a way to better understand their current and future financial needs, and look for all the ways to be helpful to them.",
            "keywords": [
                "Circumstances",
                "change over time",
                "implementing",
                "way to",
                "understand",
                "current, and future financial needs",
                "look for all",
                "ways",
                "be helpful",
            ],
        },
        {
            "script": "I have helped others save time and money, and I would like to ask you a few questions to see if we can do the same for you.",
            "keywords": [
                "helped others save time and money",
                "ask",
                "a few questions",
                "see if",
                "can do",
                "same for you",
            ],
        },
        {
            "script": "it is a complimentary service we provide and, of course, everything will remain confidential.",
            "keywords": ["complimentary service", "confidential"],
        },
        {
            "script": "This usually takes only about 10 – 15 minutes.",
            "keywords": ["about 10 – 15 minutes"],
        },
        {
            "script": "I'd like to get started right now.",
            "keywords": ["get started", "now"],
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
