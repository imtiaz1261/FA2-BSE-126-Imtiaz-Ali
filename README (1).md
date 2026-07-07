# Token Cost Calculator (using tiktoken)

Ek simple Python script jo:
1. Ek prompt leta hai
2. `tiktoken` library se uske tokens count karta hai
3. Ek (simulated) response generate karta hai
4. Input + output tokens ke hisab se total cost calculate karta hai

Ye script kisi bhi paid API key ke bina chalti hai — response yahan simulate kiya gaya hai
taake token counting aur cost calculation ka pura flow test ho sake bina billing ke.
![Script Output](./screenshots/output.png)
---

## Requirements

- Python 3.8+
- `tiktoken` library

---

## Installation

Terminal (ya VS Code terminal) mein ye command chalao:

```bash
python -m pip install tiktoken
```

Agar `pip` command directly kaam na kare, `python -m pip` use karo (upar wala command).

---

## Usage

Script run karne ke liye:

```bash
python task2.py
```

(Apni file ka actual naam yahan likho agar `task2.py` se alag rakha ho.)

---

## Output Example

```
Prompt: Explain the concept of asynchronous programming in Python with a real-world analogy.

Input tokens: 16
Response: This is a simulated response to the prompt: 'Explain the concept of asynchronous progra...'

Output tokens: 22

--- Cost Report ---
Model: gpt-4o
Input tokens:  16 ($0.00004)
Output tokens: 22 ($0.00022)
Total cost for this run: $0.00026
```

---

## How It Works

| Function | Kaam |
|---|---|
| `count_tokens()` | Diye gaye text ko `tiktoken` encoding se tokens mein todta hai aur count return karta hai |
| `calculate_cost()` | Input aur output tokens ke hisab se cost calculate karta hai (pricing table ke rates use karke) |
| `simulate_response()` | Real API call ki jagah ek dummy response deta hai — future mein real API call se replace kiya ja sakta hai |

---

## Customizing Pricing

`PRICING` dictionary mein rates diye gaye hain (per 1000 tokens):

```python
PRICING = {
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
}
```

**Note:** Ye example rates hain. Real project ke liye latest official pricing OpenAI ki website se check kar ke update kar lena.

---

## Connecting to a Real API (Optional / Future Step)

Abhi `simulate_response()` function ek dummy response deta hai. Agar future mein real LLM API
(jese OpenAI ya Anthropic) use karni ho, to bas isi function ko real API call se replace karo —
baaki poora code (token counting, cost calculation) waisa hi rahega.

---

## Project Structure

```
task2/
├── task2.py       # Main script
└── README.md       # Ye file
```
