import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
API_KEY_SECRET = os.getenv("API_KEY_SECRET")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found")

if not API_KEY_SECRET:
    raise ValueError("API_KEY_SECRET not found")

client = OpenAI(api_key=OPENAI_API_KEY)
