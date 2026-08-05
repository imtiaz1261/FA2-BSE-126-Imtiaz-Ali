import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

def generate(name, skills, experience, role):
    if not API_KEY:
        raise RuntimeError("GROQ_API_KEY is missing. Add it to .env.")
    client = Groq(api_key=API_KEY)
    prompt = f"""Create 3 ready-to-send professional cover letters.

Applicant: {name}
Skills: {skills}
Experience: {experience}
Target role: {role}

Create exactly:
1. FORMAL - polished corporate tone
2. FRIENDLY - warm, confident, professional
3. CONCISE - short, direct, impactful

Use only the provided facts. Do not invent degrees, companies,
achievements, certifications, or years of experience. Tailor each
letter to the target role and include professional openings/closings.
Clearly label each version."""
    r = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role":"system","content":"You are an expert career writer."},
            {"role":"user","content":prompt}
        ],
        temperature=0.7
    )
    return r.choices[0].message.content

def main():
    print("="*65)
    print("AI PROFESSIONAL COVER LETTER GENERATOR")
    print("="*65)
    name = input("\nName: ").strip()
    skills = input("Skills: ").strip()
    experience = input("Experience: ").strip()
    role = input("Job role: ").strip()
    if not all([name, skills, experience, role]):
        print("Please provide all four inputs.")
        return
    try:
        print("\n" + generate(name, skills, experience, role))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
