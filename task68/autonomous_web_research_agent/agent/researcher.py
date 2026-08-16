import time, json
from pathlib import Path
from .config import settings
from .llm import LLM
from .search import web_search
from .notes import ResearchNotes, Note
from .prompts import PLANNER_SYSTEM, SOURCE_SYSTEM, STOP_SYSTEM, REPORT_SYSTEM
from browser.playwright_tool import BrowserTool

class ResearchAgent:
    def __init__(self):
        self.llm = LLM()
        self.notes = ResearchNotes()
        self.visited = set()
        self.started = time.monotonic()

    def timed_out(self):
        return time.monotonic() - self.started >= settings.max_seconds

    def analyze_source(self, topic, text):
        return self.llm.json(SOURCE_SYSTEM, f"Topic: {topic}\n\nPAGE:\n{text}")

    def research(self, topic):
        plan = self.llm.json(PLANNER_SYSTEM, f"Research topic: {topic}")
        queries = plan.get("search_queries",[])[:3]
        goals = plan.get("research_goals",[])
        browser = BrowserTool(headless=True)

        try:
            for round_no in range(settings.max_search_rounds):
                if self.timed_out() or len(self.visited) >= settings.max_pages:
                    break

                candidates=[]
                for q in queries:
                    try:
                        candidates.extend(web_search(q,6))
                    except Exception as e:
                        print("[search warning]",e)

                for item in candidates:
                    if self.timed_out() or len(self.visited) >= settings.max_pages:
                        break
                    url=item["url"].split("#",1)[0]
                    if url in self.visited:
                        continue
                    self.visited.add(url)

                    try:
                        page=browser.navigate(url)
                    except Exception as e:
                        print("[browser warning]",url,e)
                        continue
                    if len(page.text)<300:
                        continue

                    try:
                        analysis=self.analyze_source(topic,page.text)
                    except Exception as e:
                        print("[analysis warning]",e)
                        continue

                    if analysis.get("relevant") is True:
                        sid=len(self.notes.load())+1
                        self.notes.append(Note(
                            sid,page.url,page.title,analysis.get("note",""),
                            page.text[:6000],analysis.get("relevance","medium")
                        ))
                        print(f"[source {sid}] {page.title} | {page.url}")

                current=self.notes.load()
                if len(current)>=3:
                    decision=self.llm.json(
                        STOP_SYSTEM,
                        f"Topic: {topic}\nGoals: {json.dumps(goals)}\n"
                        f"Collected notes:\n{json.dumps([{k:n[k] for k in ('source_id','url','title','note','relevance')} for n in current])}"
                    )
                    if decision.get("stop") is True:
                        break
                    queries=decision.get("next_queries",[])[:2] or queries[:2]
                if round_no == settings.max_search_rounds-1:
                    break
        finally:
            browser.close()

        return self.write_report(topic)

    def write_report(self, topic):
        notes=self.notes.load()
        if not notes:
            raise RuntimeError("No useful sources collected.")
        evidence=[]
        for n in notes:
            evidence.append(
                f"SOURCE [{n['source_id']}]\nTitle: {n['title']}\nURL: {n['url']}\n"
                f"Relevance: {n['relevance']}\nNote: {n['note']}\nEvidence: {n['extracted_text'][:5000]}"
            )
        report=self.llm.complete(REPORT_SYSTEM, f"Topic: {topic}\n\n"+"\n\n".join(evidence),.15)
        Path("reports").mkdir(exist_ok=True)
        safe="".join(c if c.isalnum() or c in " -_" else "_" for c in topic)
        path=Path("reports")/("_".join(safe.split())[:80]+".md")
        path.write_text(report,encoding="utf-8")
        return str(path)
