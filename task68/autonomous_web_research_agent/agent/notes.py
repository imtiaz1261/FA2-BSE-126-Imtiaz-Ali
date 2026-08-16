from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime, timezone
import json

@dataclass
class Note:
    source_id: int
    url: str
    title: str
    note: str
    extracted_text: str
    relevance: str

class ResearchNotes:
    def __init__(self, path="storage/running_notes.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, note):
        record = asdict(note)
        record["timestamp"] = datetime.now(timezone.utc).isoformat()
        with self.path.open("a",encoding="utf-8") as f:
            f.write(json.dumps(record,ensure_ascii=False)+"\n")

    def load(self):
        if not self.path.exists():
            return []
        return [json.loads(x) for x in self.path.read_text(encoding="utf-8").splitlines() if x.strip()]
