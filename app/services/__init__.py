from __future__ import annotations

import os
from typing import Iterable

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY environment variable is not set.")

genai.configure(api_key=api_key)

if not os.getenv("GEMINI_MODEL"):
    os.environ["GEMINI_MODEL"] = "models/gemini-2.5-flash"

if not os.getenv("GEMINI_EMBEDDING_MODEL"):
    os.environ["GEMINI_EMBEDDING_MODEL"] = "models/text-embedding-004"
