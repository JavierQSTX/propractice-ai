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
#     "challenge": "1",
#     "question": "You have resolved an issue for an existing Customer. What should you say to transition into the Customer Review?",
#     "briefing": "<p>This module trains bankers at Northfield Bank to proactively initiate essential financial review conversations with clients. You will learn to transition into a client review after resolving an issue, or when engaging new or existing clients. The objective is to confidently identify evolving financial needs, offer relevant solutions, and deepen client relationships by demonstrating a commitment to their long-term financial well-being through confidential, complimentary service. In the assessment, you will respond to client statements, focusing on acknowledging their situation, stating your responsibility to help achieve financial goals, explaining the benefits of a review (understanding needs, finding helpful solutions, potentially saving time/money), and clearly communicating the complimentary, confidential, and time-efficient nature of the service, all while using a formal and precise tone.</p>",
#     "keyElements": [
#         {
#             "script": "Mr. Jackson ( Customer Name ), what else can I assist you with today ?",
#             "keywords": ["Customer Name", "what else", "assist", "with today"],
#         },
#         {
#             "script": "Thank you for being a Northfield Bank Customer. I appreciate the opportunity to serve you .",
#             "keywords": ["Thank you", "appreciate", "opportunity", "serve you"],
#         },
#         {
#             "script": "One of my responsibilities is to help Customers achieve their financial goals and make their banking more convenient .",
#             "keywords": [
#                 "responsibilities",
#                 "help Customers achieve",
#                 "financial goals",
#                 "make",
#                 "banking",
#                 "convenient",
#             ],
#         },
#         {
#             "script": "Circumstances for our Customers typically change over time , and we are implementing a way to better understand our Customers’ current , and future financial needs , and look for all the ways to be helpful to them.",
#             "keywords": [
#                 "Circumstances",
#                 "change over time",
#                 "implementing",
#                 "way to",
#                 "understand",
#                 "current",
#                 "future financial needs",
#                 "look",
#                 "all",
#                 "ways",
#                 "helpful",
#             ],
#         },
#         {
#             "script": "It is a complimentary service we provide and, of course, everything will remain confidential .",
#             "keywords": ["complimentary service", "confidential"],
#         },
#         {
#             "script": "This usually takes only about 10 to 15 minutes .",
#             "keywords": ["about 10 to 15 minutes"],
#         },
#         {
#             "script": "Let’s get this started for you right now .",
#             "keywords": ["started", "now"],
#         },
#     ],
#     "user_id": "",
#     "tags": ["test tss (Duplicate)", "Challenge 1 New Member Entry Line"],
# }


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
