import os
from dotenv import load_dotenv
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

load_dotenv()
API_KEY=os.getenv("GROQ_API_KEY")
MODEL=os.getenv("GROQ_MODEL","llama-3.3-70b-versatile")

def retryable(exc):
    code=getattr(exc,"status_code",None)
    return code is None or code == 429 or code >= 500

@retry(
    retry=retry_if_exception(retryable),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1,min=1,max=8),
    reraise=True,
)
def call_api(prompt):
    client=Groq(api_key=API_KEY)
    return client.chat.completions.create(
        model=MODEL,
        messages=[{"role":"user","content":prompt}],
        temperature=0.2,
    )

def main():
    print("Groq API + Tenacity Retry Demo")
    if not API_KEY:
        print("Error: GROQ_API_KEY is missing from .env")
        return
    prompt=input("Enter prompt: ").strip()
    if not prompt:
        print("Prompt cannot be empty.")
        return
    try:
        print("Calling API (maximum 3 attempts)...")
        response=call_api(prompt)
        print("\n--- Response ---")
        print(response.choices[0].message.content)
    except Exception as exc:
        print(f"API request failed after 3 attempts: {exc}")

if __name__=="__main__":
    main()
