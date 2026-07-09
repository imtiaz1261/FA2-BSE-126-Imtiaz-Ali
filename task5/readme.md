# Dynamic Email Draft Generator

Generates an email draft from a **topic** and a **tone** (professional or
funny), using a `PromptTemplate` with two input variables run through an
LCEL chain (`prompt | model | output_parser`).

## What it demonstrates

- A `ChatPromptTemplate` with multiple placeholders (`{topic}`, `{tone}`)
- Passing a dict of variables into `chain.invoke({...})`
- How the same chain structure adapts its output just by changing the
  input values — no code changes needed to switch tone or topic

## Files

| File                    | Purpose                                       |
|--------------------------|------------------------------------------------|
| `email_generator.py`    | Main script — run this                        |
| `requirements.txt`      | Python dependencies                           |
| `secret_key.py`         | Your API key (never commit this file)         |
| `.gitignore`            | Keeps `secret_key.py` out of version control   |

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

3. **Add your API key** in `secret_key.py` (get a free one at
   [console.groq.com/keys](https://console.groq.com/keys)).

## Usage

**Interactive mode:**
```
python email_generator.py
```
It will prompt you for a topic and a tone.

**Command-line mode:**
```
python email_generator.py --topic "asking for a deadline extension" --tone professional
python email_generator.py --topic "reminding the team about the office party" --tone funny
```

## Example output

```
Subject: Request for Deadline Extension

Dear [Manager's Name],

I hope this email finds you well. I am writing to request a short
extension on the upcoming project deadline...

Best regards,
[Your Name]
```

## Notes

- The tone parameter isn't hardcoded to just two values — the prompt
  instructs the model on how to handle "professional" and "funny"
  specifically, but you can pass other tones (e.g. "urgent",
  "apologetic") and the model will still adapt reasonably.