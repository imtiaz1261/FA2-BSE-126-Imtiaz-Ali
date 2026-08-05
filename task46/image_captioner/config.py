"""
Configuration loader.

Reads settings from a local .env file only. No API key is ever hardcoded
here — create your own .env from .env.example and keep it local; it's
already excluded via .gitignore.
"""

import os
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Vision-capable model. Groq and OpenAI both rename/retire vision models
# periodically — if this default 404s, check the provider's current model
# list and update VISION_MODEL_NAME in your .env.
VISION_MODEL_NAME = os.getenv("VISION_MODEL_NAME", "qwen/qwen3.6-27b")
