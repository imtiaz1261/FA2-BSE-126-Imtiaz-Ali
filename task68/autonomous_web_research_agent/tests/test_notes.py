from agent.notes import ResearchNotes, Note

def test_notes(tmp_path):
    p=tmp_path/"notes.jsonl"
    n=ResearchNotes(str(p))
    n.append(Note(1,"https://example.com","Example","Useful","Evidence","high"))
    data=n.load()
    assert len(data)==1
    assert data[0]["url"]=="https://example.com"
