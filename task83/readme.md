# Task 83 — Structured Recipe Generator

A LangChain-based application that generates recipes in a **strict, validated structure** using Pydantic. Instead of returning unstructured AI text, the application converts the model response into a reliable Python object that can be safely used by other parts of the application.

## What it demonstrates

* Creating a structured `Recipe` schema using Pydantic `BaseModel`.
* Using `PydanticOutputParser` to define and enforce the expected output format.
* Automatically providing formatting instructions to the LLM through the prompt.
* Validating the generated response and detecting missing or incorrectly typed fields.
* Building an LCEL pipeline using `prompt | model | parser`.
* Converting AI-generated recipe information into predictable structured data.

## Files

| File                   | Purpose                                       |
| ---------------------- | --------------------------------------------- |
| `structured_recipe.py` | Main application script                       |
| `requirements.txt`     | Required Python dependencies                  |
| `secret_key.py`        | Stores the API key locally                    |
| `.gitignore`           | Prevents sensitive files from being committed |

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

### 3. Configure the API key

Add your Groq API key to `secret_key.py`.

Get an API key from:

https://console.groq.com/keys

## Usage

### Interactive Mode

```powershell
python structured_recipe.py
```

The application will ask you to enter the dish you want to generate.

### Command-Line Mode

```powershell
python structured_recipe.py --dish "chicken karahi"
```

Another example:

```powershell
python structured_recipe.py --dish "vegetable pasta"
```

## Example Output

```text
=== Validated Recipe Object ===

name: Chicken Karahi

ingredients:
[
    "500g chicken",
    "3 tomatoes",
    "2 green chilies",
    "1 teaspoon ginger garlic paste",
    "1 teaspoon red chili powder"
]

steps:
[
    "Heat oil in a pan.",
    "Add ginger garlic paste and cook briefly.",
    "Add chicken and cook until lightly browned.",
    "Add tomatoes and spices.",
    "Cook until the chicken is fully done."
]

=== Structured JSON ===

{
    "name": "Chicken Karahi",
    "ingredients": [
        "500g chicken",
        "3 tomatoes",
        "2 green chilies"
    ],
    "steps": [
        "Heat oil in a pan.",
        "Add ginger garlic paste and cook briefly.",
        "Add chicken and spices and cook until done."
    ]
}
```

## Why Pydantic Validation Matters

LLMs can sometimes return incomplete or incorrectly formatted data. Pydantic validation ensures that the generated recipe follows the expected schema before the data is passed to other parts of the application.

For example, if `ingredients` should be a list but the model returns a single string, the parser can detect the mismatch immediately instead of allowing invalid data to continue through the application.

## Notes

* A low temperature setting can be used to make structured responses more consistent.
* Parser errors can be caught and handled with a retry mechanism.
* The project can later be extended with `OutputFixingParser` or other structured-output techniques.
* The same architecture can be adapted for product information, movie data, travel plans, study notes, or other structured AI outputs.

**Task 83 demonstrates how Pydantic and LangChain can transform flexible LLM responses into reliable, validated application data.**
