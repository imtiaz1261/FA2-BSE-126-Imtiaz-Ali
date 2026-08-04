"""
Configuration loader.

This file does NOT contain any real API key. It only reads values from
a local .env file (which you create yourself from .env.example and never
commit or share). Keeping config in one small module means the rest of
the code just does `from config import GROQ_API_KEY` instead of repeating
os.getenv() calls everywhere.
"""

import os
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.1-8b-instant")
