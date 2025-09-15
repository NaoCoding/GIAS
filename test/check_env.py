from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

if not os.getenv("OPEN_ROUTER_API_KEY"):
  raise ValueError("OPEN_ROUTER_API_KEY not set in .env file")


print("Passed All Environment Variables Test")