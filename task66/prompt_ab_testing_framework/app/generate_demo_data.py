from __future__ import annotations
import argparse, random, uuid, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.database import insert_interaction

TASKS = [
    "Explain recursion in Python with a simple example.",
    "Give three interview tips for a software engineering student.",
    "Summarize the difference between SQL and NoSQL.",
    "Create a short study plan for learning FastAPI.",
    "Explain what an API is in simple terms.",
    "Suggest debugging steps for a Python import error."
]

def generate(n=120, seed=42):
    rng = random.Random(seed)
    start = datetime.now(timezone.utc) - timedelta(days=7)
    for i in range(n):
        variant = "A" if rng.random() < 0.5 else "B"
        completed = int(rng.random() < (0.64 if variant == "A" else 0.76))
        feedback = "up" if rng.random() < (0.68 if variant == "A" else 0.79) else "down"
        words = max(25, int(rng.gauss(105 if variant == "A" else 115, 22)))
        response = f"Demo response for Variant {variant}. " + ("Example. " * max(8, words//8))
        insert_interaction(
            str(uuid.uuid4()), (start+timedelta(minutes=i*13)).isoformat(),
            rng.choice(TASKS), variant, response[:words*7], words,
            feedback, completed,
            round(max(0, min(1, rng.gauss(0.73 if variant=="A" else 0.81, 0.08))), 3))
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=120)
    args = parser.parse_args()
    if args.n < 100:
        raise SystemExit("--n must be at least 100")
    generate(args.n)
    print(f"Inserted {args.n} synthetic interactions.")
