import os

from dotenv import load_dotenv

load_dotenv()

required_keys = ["OPEN_ROUTER_API_KEY", "GITHUB_TOKEN", "MODEL_NAME"]

for key in required_keys:
    # print(key, os.getenv(key))
    if not os.getenv(key):
        raise ValueError(f"{key} not set in .env file")

print("Passed All Environment Variables Test")
