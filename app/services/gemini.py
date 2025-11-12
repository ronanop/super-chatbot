from __future__ import annotations

import os
from typing import Iterable

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY environment variable is not set.")

DEFAULT_GENERATION_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash")
genai.configure(api_key=api_key)

_model_cache: dict[str, genai.GenerativeModel] = {}


def get_generation_model(model_name: str | None = None) -> genai.GenerativeModel:
    name = model_name or DEFAULT_GENERATION_MODEL
    if name not in _model_cache:
        _model_cache[name] = genai.GenerativeModel(name)
    return _model_cache[name]
