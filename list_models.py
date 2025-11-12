import google.generativeai as genai
import os

from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise SystemExit("GEMINI_API_KEY not set")

genai.configure(api_key=api_key)

print("Available models:\n----------------")
for model in genai.list_models():
    if "generateContent" in model.supported_generation_methods:
        print(model.name)
