"""
Unstructured Text -> Structured JSON Extractor
================================================
Yeh script kisi bhi unstructured text (resume ya product description) ko
LLM (Groq - Llama 3.3 70B) prompt ke through structured JSON mein convert
karta hai:

- Resume        -> { name, skills, experience }
- Product desc. -> { name, price, features }

Output ko Pydantic se validate kiya jata hai, aur agar valid ho to use
neatly print kiya jata hai (invalid hone par error clearly dikhaya jata hai).

Setup:
    1. `.env.example` ko `.env` mein copy karein aur apni Groq API key
       aur model daalein:
        GROQ_API_KEY=your-api-key-here
        GROQ_MODEL=llama-3.3-70b-versatile

Run:
    python main.py
"""

import os
import sys
import json
from typing import List, Optional

from dotenv import load_dotenv
from groq import Groq
from pydantic import BaseModel, ValidationError, field_validator

load_dotenv()


# ---------------------------------------------------------------------------
# 1. Sample unstructured inputs (aap inhe apne data se replace kar sakte hain)
# ---------------------------------------------------------------------------
SAMPLE_INPUTS = [
    {
        "type": "resume",
        "text": """
            Ayesha Khan is a Software Engineer with 4 years of experience
            building web applications. She is proficient in Python,
            JavaScript, React, and PostgreSQL, and has led a team of 3
            developers at her current company, TechNova Solutions, for the
            past 2 years. Before that, she worked as a Junior Developer at
            CodeWorks for 2 years.
        """,
    },
    {
        "type": "product",
        "text": """
            Introducing the UltraSound Pro Wireless Earbuds, priced at
            $89.99. These earbuds feature active noise cancellation,
            30-hour battery life with the charging case, IPX5 water
            resistance, and Bluetooth 5.3 connectivity for a stable,
            low-latency connection.
        """,
    },
    {
        "type": "resume",
        "text": """
            Bilal Ahmed, Data Analyst. 3 years of experience working with
            SQL, Excel, Power BI, and Python (pandas). Currently working
            at Insight Analytics as a Senior Data Analyst for 1 year, and
            previously spent 2 years at DataWorks as a Data Analyst.
        """,
    },
]


# ---------------------------------------------------------------------------
# 2. Pydantic schemas — output validation ke liye
# ---------------------------------------------------------------------------
class ResumeSchema(BaseModel):
    name: str
    skills: List[str]
    experience: str

    @field_validator("skills")
    @classmethod
    def skills_not_empty(cls, v):
        if not v:
            raise ValueError("skills list should not be empty")
        return v


class ProductSchema(BaseModel):
    name: str
    price: str
    features: List[str]

    @field_validator("features")
    @classmethod
    def features_not_empty(cls, v):
        if not v:
            raise ValueError("features list should not be empty")
        return v


SCHEMA_MAP = {
    "resume": ResumeSchema,
    "product": ProductSchema,
}


# ---------------------------------------------------------------------------
# 3. LLM prompt templates
# ---------------------------------------------------------------------------
RESUME_PROMPT = """You are an information extraction assistant.

From the resume text below, extract the following fields and return
ONLY a valid JSON object, with no explanation, no markdown, no code
fences — just raw JSON:

{{
  "name": "<full name of the person>",
  "skills": ["<skill1>", "<skill2>", ...],
  "experience": "<a short summary of their work experience, in one or two sentences>"
}}

Resume Text:
\"\"\"{text}\"\"\"

JSON:"""

PRODUCT_PROMPT = """You are an information extraction assistant.

From the product description below, extract the following fields and
return ONLY a valid JSON object, with no explanation, no markdown, no
code fences — just raw JSON:

{{
  "name": "<product name>",
  "price": "<price as a string, including currency symbol if present>",
  "features": ["<feature1>", "<feature2>", ...]
}}

Product Description:
\"\"\"{text}\"\"\"

JSON:"""

PROMPT_MAP = {
    "resume": RESUME_PROMPT,
    "product": PRODUCT_PROMPT,
}


# ---------------------------------------------------------------------------
# 4. Core extraction logic
# ---------------------------------------------------------------------------
def clean_json_string(raw: str) -> str:
    """Remove markdown code fences etc, in case the model adds them anyway."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
    return raw.strip()


def extract_structured_data(client: Groq, model: str, text: str, doc_type: str) -> dict:
    """Call the LLM and return the raw parsed JSON (before validation)."""
    prompt = PROMPT_MAP[doc_type].format(text=text)

    response = client.chat.completions.create(
        model=model,
        max_tokens=500,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
    )

    raw_output = response.choices[0].message.content
    cleaned = clean_json_string(raw_output)
    return json.loads(cleaned)


def validate_structured_data(doc_type: str, data: dict) -> BaseModel:
    """Validate extracted dict against the correct Pydantic schema."""
    schema = SCHEMA_MAP[doc_type]
    return schema(**data)


def process_item(client: Groq, model: str, doc_type: str, text: str) -> None:
    print("=" * 70)
    print(f"INPUT TYPE: {doc_type}")
    print(f"RAW TEXT: {text.strip()[:120]}...")
    print("-" * 70)

    try:
        raw_json = extract_structured_data(client, model, text, doc_type)
    except (json.JSONDecodeError, Exception) as exc:
        print(f"❌ LLM did not return valid JSON. Error: {exc}")
        return

    try:
        validated = validate_structured_data(doc_type, raw_json)
        print("✅ Valid structured output:\n")
        print(json.dumps(validated.model_dump(), indent=2, ensure_ascii=False))
    except ValidationError as exc:
        print("❌ Validation failed. Raw LLM output was:\n")
        print(json.dumps(raw_json, indent=2, ensure_ascii=False))
        print("\nValidation errors:")
        print(exc)

    print()


def main():
    api_key = os.environ.get("GROQ_API_KEY")
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

    if not api_key:
        print("ERROR: GROQ_API_KEY not set.")
        print("Copy .env.example to .env and add your Groq API key, or:")
        print('  export GROQ_API_KEY="your-api-key-here"')
        sys.exit(1)

    client = Groq(api_key=api_key)

    for item in SAMPLE_INPUTS:
        process_item(client, model, item["type"], item["text"])


if __name__ == "__main__":
    main()
