# Task 82 — Smart Message Composer

An AI-powered message generation tool that creates customized email drafts based on a user-provided **subject** and **writing style**. It uses LangChain's prompt templates and an LCEL pipeline to dynamically generate responses without changing the application code.

## What it demonstrates

* Using `ChatPromptTemplate` with multiple dynamic input variables.
* Passing user-provided values into an LCEL chain using `chain.invoke({...})`.
* Dynamically modifying the generated message based on subject and style.
* Separating prompt logic, model processing, and output parsing into a simple pipeline.
* Reusing the same AI workflow for different types of email content.

## Files

| File                  | Purpose                                       |
| --------------------- | --------------------------------------------- |
| `message_composer.py` | Main application script                       |
| `requirements.txt`    | Required Python packages                      |
| `secret_key.py`       | Stores the API key locally                    |
| `.gitignore`          | Prevents sensitive files from being committed |

## Setup

### 1. Create and activate a virtual environment

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure your API key

Add your Groq API key to `secret_key.py`.

Get an API key from:

https://console.groq.com/keys

## Usage

### Interactive Mode

```powershell
python message_composer.py
```

The program will ask for the message subject and preferred writing style.

### Command-Line Mode

```powershell
python message_composer.py --subject "project meeting reminder" --style formal
```

Another example:

```powershell
python message_composer.py --subject "team lunch invitation" --style friendly
```

## Example Output

```text
Subject: Project Meeting Reminder

Hello Team,

This is a reminder about our upcoming project meeting.
We will discuss the current progress, pending tasks, and
the next development milestones.

Best regards,
[Your Name]
```

## Notes

The style input is flexible and is not restricted to predefined values. You can use styles such as **formal, friendly, concise, persuasive, humorous, apologetic, or urgent**, and the AI model will adjust the generated message accordingly.

**Task 82 demonstrates how dynamic prompt variables can make a single LangChain workflow reusable for many different email-generation scenarios.**
