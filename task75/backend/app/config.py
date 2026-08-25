import os
from dotenv import load_dotenv
load_dotenv()
GITHUB_TOKEN=os.getenv("GITHUB_TOKEN","")
GITHUB_WEBHOOK_SECRET=os.getenv("GITHUB_WEBHOOK_SECRET","")
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY","")
OPENAI_MODEL=os.getenv("OPENAI_MODEL","gpt-4o-mini")
OPENAI_BASE_URL=os.getenv("OPENAI_BASE_URL") or None
MIN_SEVERITY=os.getenv("MIN_SEVERITY","suggestion").lower()
MAX_FINDINGS=int(os.getenv("MAX_FINDINGS","12"))
DRY_RUN=os.getenv("DRY_RUN","false").lower()=="true"
