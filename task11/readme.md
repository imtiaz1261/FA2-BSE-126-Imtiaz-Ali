# CLI Chatbot with 5-Message Memory

A command-line chatbot that remembers only the **last 5 user messages**
(and their matching replies), so it can answer follow-up questions
correctly, without letting the conversation grow unbounded.

## What it demonstrates

- `collections.deque(maxlen=5)` — a sliding window that automatically
  drops the oldest item once a 6th is added, with no manual trimming
  logic required.
- Building the message list sent to the API from that bounded history,
  so the model always sees the most recent context but never the entire
  conversation.

## Files

| File                  | Purpose                                     |
|-------------------------|------------------------------------------------|
| `memory_chatbot.py`   | Main script — run this                       |
| `requirements.txt`    | Python dependencies                          |
| `secret_key.py`       | Your API key (never commit this file)        |
| `.gitignore`          | Keeps `secret_key.py` out of version control  |

## Setup

1. **Create and activate a virtual environment**
   ```
   python -m venv venv
   venv\Scripts\Activate.ps1
   ```

2. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

3. **Add your API key** in `secret_key.py`.

## Usage

```
python memory_chatbot.py
```

Change how many messages it remembers:
```
python memory_chatbot.py --memory-size 3
```

## Example — proving it remembers follow-ups

```
You: My favorite color is blue.
Assistant: Got it, blue is your favorite color!

You: What's my favorite color?
Assistant: Your favorite color is blue.
```

## Example — proving it forgets after 5 messages

```
You: message 1: remember the number 42
...
You: message 2, 3, 4, 5, 6 (five more messages)...
You: What number did I ask you to remember?
Assistant: I don't have that in our recent conversation — could you remind me?
```
Once a 6th user message is sent, the 1st one (and its reply) is dropped
from memory — this is expected, deliberate behavior, not a bug.

## How the memory logic works

```python
self.history: deque = deque(maxlen=memory_size)
```
Each entry is one `(user_message, assistant_reply)` pair. When `.append()`
is called on a full deque, Python automatically removes the oldest entry
first — that single line is the entire "forget old messages" mechanism.

Every time `ask()` is called, `_build_messages()` reconstructs the full
message list sent to the API: the system prompt, then every remembered
pair in order, then the new message. Since `self.history` never holds
more than 5 pairs, the message list sent to the API never grows past a
fixed size either — this is what keeps token usage (and cost) bounded
even in a very long-running session.

## Tested

The memory-trimming logic was verified with a mocked client: after 7
simulated turns, the bot correctly remembered only messages 3 through 7
and had forgotten messages 1 and 2.