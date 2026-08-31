import os
from dotenv import load_dotenv
from groq import Groq
load_dotenv()

def generate_personalized_tip(result: dict) -> str:
    key=os.getenv('GROQ_API_KEY')
    if not key: raise RuntimeError('GROQ_API_KEY is missing from .env')
    failed=[k for k,v in result['checks'].items() if not v]
    prompt=f'''Give one concise password-security improvement tip. The password itself is NOT provided. Aggregate results only: score={result["score"]}/100; label={result["label"]}; length={result["length"]}; failed checks={", ".join(failed) if failed else "none"}. Never ask for or reconstruct the password. Recommend a memorable passphrase, password manager, or missing rule. Under 60 words.'''
    r=Groq(api_key=key).chat.completions.create(model=os.getenv('GROQ_MODEL','llama-3.3-70b-versatile'),temperature=0.4,messages=[{'role':'system','content':'You are a concise password-security coach. Never request or expose secret passwords.'},{'role':'user','content':prompt}])
    return r.choices[0].message.content.strip()
