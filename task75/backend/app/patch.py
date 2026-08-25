import re
HUNK=re.compile(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
def changed_lines(patch):
    out=set(); cur=None
    for x in (patch or "").splitlines():
        if x.startswith("@@"):
            m=HUNK.search(x)
            if m: cur=int(m.group(1))
            continue
        if cur is None or x.startswith("\\"): continue
        if x.startswith("+") and not x.startswith("+++"): out.add(cur); cur+=1
        elif x.startswith("-") and not x.startswith("---"): pass
        else: cur+=1
    return out
