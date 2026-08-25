import json
from openai import OpenAI
from . import config
SYSTEM='''You are ReviewSphere, a senior software engineer reviewing a GitHub pull request.
Only report issues supported by evidence in the supplied patch.
Find correctness bugs, security vulnerabilities, meaningful reliability/performance risks, maintainability smells, and missing/inadequate tests.
Avoid subjective style preferences, hypothetical issues, harmless refactors and duplicates.
Severity: critical=severe security/correctness/data-loss/crash risk; suggestion=meaningful bug/security/regression/test issue; nitpick=low-risk improvement.
Return JSON only with summary and findings. Each finding has severity, confidence, title, body, path, line, side. Use line=null if it cannot confidently map to a changed RIGHT-side line.'''
class Reviewer:
    def __init__(self):
        kw={"api_key":config.OPENAI_API_KEY}
        if config.OPENAI_BASE_URL: kw["base_url"]=config.OPENAI_BASE_URL
        self.client=OpenAI(**kw)
    def run(self,title,body,diff):
        prompt=f"PR TITLE:\n{title}\n\nDESCRIPTION:\n{body[:10000]}\n\nDIFF:\n{diff[:120000]}"
        r=self.client.chat.completions.create(model=config.OPENAI_MODEL,temperature=.1,response_format={"type":"json_object"},messages=[{"role":"system","content":SYSTEM},{"role":"user","content":prompt}])
        return json.loads(r.choices[0].message.content)
