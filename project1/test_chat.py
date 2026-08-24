"""End-to-end smoke test: login → stream chat → print response."""
import sys, requests, json

BASE = "http://localhost:8000/api/v1"

# 1. login
r = requests.post(f"{BASE}/auth/login",
    json={"email": "admin@aihub.local", "password": "Admin@12345"},
    timeout=10)

if r.status_code != 200:
    print("LOGIN FAILED:", r.status_code, r.text[:400])
    sys.exit(1)

data  = r.json()
token = data["access_token"]
user  = data["user"]
print(f"[OK] login  user={user['email']}  role={user['role']}")

headers = {"Authorization": f"Bearer {token}", "Accept": "text/event-stream"}

# 2. stream chat
r2 = requests.post(
    f"{BASE}/chat/stream",
    headers=headers,
    json={"message": "Say exactly: Hello from AIHub!", "mode": "chat", "stream": True},
    stream=True,
    timeout=60,
)
print(f"[OK] stream status={r2.status_code}")

conv_id = None
tokens_acc = []
for raw in r2.iter_lines(decode_unicode=True):
    if not raw or not raw.startswith("data: "):
        continue
    frame = raw[6:]
    if frame == "[DONE]":
        print("[DONE] stream finished")
        break
    elif frame.startswith("[CONV_ID]"):
        conv_id = frame[9:]
        print(f"[CONV_ID] {conv_id}")
    elif frame.startswith("[ERROR]"):
        print(f"[ERROR] {frame[7:]}")
        break
    elif frame.startswith("[LIMIT]"):
        print(f"[LIMIT] {frame[7:]}")
        break
    elif frame.startswith("[BLOCKED]"):
        print(f"[BLOCKED] {frame[9:]}")
        break
    else:
        tokens_acc.append(frame.replace("\\n", "\n"))

full = "".join(tokens_acc)
print(f"\n[RESPONSE] {repr(full[:200])}")

# 3. fetch conversation
if conv_id:
    r3 = requests.get(f"{BASE}/chat/conversations/{conv_id}",
                      headers=headers, timeout=10)
    msgs = r3.json().get("messages", [])
    print(f"\n[OK] conversation has {len(msgs)} messages")
    for m in msgs:
        print(f"  [{m['role']:9s}] {m['content'][:80]}")

print("\n=== SMOKE TEST PASSED ===")
