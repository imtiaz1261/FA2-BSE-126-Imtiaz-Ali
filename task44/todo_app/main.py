"""
Natural Language To-Do App
==========================
User natural language mein command deta hai (jaise "kal 5 baje doctor
appointment add karo"), aur LLM (Groq - Llama 3.3 70B) usay structured
task (title, date, time) mein convert karke ek list mein save karta hai.
Tasks `tasks.json` file mein persist hote hain, taake app band karne ke
baad bhi data safe rahe.

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
from datetime import date, datetime
from typing import List, Optional

from dotenv import load_dotenv
from groq import Groq
from pydantic import BaseModel, ValidationError, field_validator

load_dotenv()

TASKS_FILE = "tasks.json"


# ---------------------------------------------------------------------------
# 1. Pydantic schema — LLM output validation ke liye
# ---------------------------------------------------------------------------
class Task(BaseModel):
    title: str
    date: str  # format: YYYY-MM-DD
    time: Optional[str] = None  # format: HH:MM (24-hour), ya null agar na di ho

    @field_validator("date")
    @classmethod
    def validate_date_format(cls, v):
        datetime.strptime(v, "%Y-%m-%d")  # raises ValueError if invalid
        return v

    @field_validator("time")
    @classmethod
    def validate_time_format(cls, v):
        if v is None or v == "":
            return None
        datetime.strptime(v, "%H:%M")  # raises ValueError if invalid
        return v


# ---------------------------------------------------------------------------
# 2. LLM prompt template
# ---------------------------------------------------------------------------
TASK_PROMPT = """You are a task extraction assistant for a to-do app.

Today's date is {today} ({weekday}). The user may write the command in
English, Urdu (Roman or script), or a mix of both.

From the user's natural language command below, extract a structured
task. Resolve any relative dates/times (e.g. "kal" = tomorrow, "aaj" =
today, "parso" = day after tomorrow, "agle hafte" = next week, "5 baje"
= 17:00 or 05:00 based on context) into absolute values based on
today's date.

Return ONLY a valid JSON object, with no explanation, no markdown, no
code fences — just raw JSON, in this exact structure:

{{
  "title": "<short task title, e.g. 'Doctor appointment'>",
  "date": "<YYYY-MM-DD>",
  "time": "<HH:MM in 24-hour format, or null if no time was mentioned>"
}}

User Command:
\"\"\"{command}\"\"\"

JSON:"""


# ---------------------------------------------------------------------------
# 3. Core logic
# ---------------------------------------------------------------------------
def clean_json_string(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
    return raw.strip()


def parse_task_from_command(client: Groq, model: str, command: str) -> dict:
    today = date.today()
    prompt = TASK_PROMPT.format(
        today=today.isoformat(),
        weekday=today.strftime("%A"),
        command=command,
    )
    response = client.chat.completions.create(
        model=model,
        max_tokens=200,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
    )
    raw_output = response.choices[0].message.content
    cleaned = clean_json_string(raw_output)
    return json.loads(cleaned)


def load_tasks() -> List[dict]:
    if not os.path.exists(TASKS_FILE):
        return []
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_tasks(tasks: List[dict]) -> None:
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)


def print_tasks(tasks: List[dict]) -> None:
    print("\n" + "=" * 55)
    print(" 📋  YOUR TO-DO LIST")
    print("=" * 55)

    if not tasks:
        print("  (koi task nahi hai abhi)")
    else:
        # Sort by date, then time
        sorted_tasks = sorted(
            tasks, key=lambda t: (t["date"], t.get("time") or "23:59")
        )
        for idx, t in enumerate(sorted_tasks, start=1):
            time_str = f" at {t['time']}" if t.get("time") else ""
            print(f"  {idx}. [{t['date']}{time_str}] {t['title']}")

    print("=" * 55)


# ---------------------------------------------------------------------------
# 4. Main app loop
# ---------------------------------------------------------------------------
def main():
    api_key = os.environ.get("GROQ_API_KEY")
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

    if not api_key:
        print("ERROR: GROQ_API_KEY not set.")
        print("Copy .env.example to .env and add your Groq API key, or:")
        print('  export GROQ_API_KEY="your-api-key-here"')
        sys.exit(1)

    client = Groq(api_key=api_key)
    tasks = load_tasks()

    print("=" * 55)
    print(" ✅  Natural Language To-Do App")
    print("=" * 55)
    print("\nCommands:")
    print("  - Koi bhi natural language command likhein task add karne ke liye")
    print("    e.g. 'kal 5 baje doctor appointment add karo'")
    print("  - 'list'  -> saari tasks dekhein")
    print("  - 'exit'  -> app band karein")

    while True:
        user_input = input("\n> ").strip()
        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            print("Task list save ho chuki hai. Allah Hafiz! 👋")
            break

        if user_input.lower() == "list":
            print_tasks(tasks)
            continue

        # Otherwise, treat it as a natural language "add task" command
        try:
            raw_json = parse_task_from_command(client, model, user_input)
        except json.JSONDecodeError as exc:
            print(f"❌ LLM ne valid JSON return nahi kiya. Error: {exc}")
            continue
        except Exception as exc:
            print(f"❌ Kuch masla hua LLM call mein: {exc}")
            continue

        try:
            task = Task(**raw_json)
        except ValidationError as exc:
            print("❌ Task extract karne mein masla hua. Raw LLM output:\n")
            print(json.dumps(raw_json, indent=2, ensure_ascii=False))
            print("\nValidation errors:")
            print(exc)
            continue

        tasks.append(task.model_dump())
        save_tasks(tasks)

        time_str = f" at {task.time}" if task.time else ""
        print(f"✅ Task add ho gayi: \"{task.title}\" — {task.date}{time_str}")


if __name__ == "__main__":
    main()
