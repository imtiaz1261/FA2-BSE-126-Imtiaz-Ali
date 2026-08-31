import os
from dotenv import load_dotenv
from groq import Groq
load_dotenv()

def generate_summary(text):
    if not text.strip(): raise ValueError('There is no text to summarize.')
    key=os.getenv('GROQ_API_KEY')
    if not key: raise RuntimeError('GROQ_API_KEY is missing from .env')
    client=Groq(api_key=key)
    response=client.chat.completions.create(
        model=os.getenv('GROQ_MODEL','llama-3.3-70b-versatile'), temperature=0.2,
        messages=[{'role':'system','content':'Summarize accurately. Return exactly 3 numbered short lines and do not invent facts.'},
                  {'role':'user','content':'Summarize this PDF text in exactly 3 numbered lines: main topic, key points, and takeaway.\n\n'+text[:30000]}])
    return response.choices[0].message.content.strip()
