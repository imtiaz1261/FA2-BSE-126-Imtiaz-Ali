from groq import Groq
from .config import settings
import json

class LLM:
    def __init__(self):
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is missing. Add it to .env.")
        self.client = Groq(api_key=settings.groq_api_key)

    def complete(self, system, user, temperature=0.1):
        r = self.client.chat.completions.create(
            model=settings.groq_model,
            temperature=temperature,
            messages=[
                {"role":"system","content":system},
                {"role":"user","content":user}
            ])
        return r.choices[0].message.content or ""

    def json(self, system, user):
        raw = self.complete(system, user, 0).strip()
        if raw.startswith("```"):
            raw = raw.split("\n",1)[1].rsplit("```",1)[0]
        return json.loads(raw)
