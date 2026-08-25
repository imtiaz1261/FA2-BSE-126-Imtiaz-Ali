"""
Recipe generator with strict JSON output.

Defines a Pydantic model (`Recipe`) describing the exact shape we want
back from the LLM, then wires a `PydanticOutputParser` into an LCEL chain:

    prompt | model | parser

The parser does two things:
1. Injects formatting instructions into the prompt telling the model
   exactly what JSON schema to produce.
2. Parses the model's raw text output back into a validated `Recipe`
   Python object — if the model returns malformed JSON or is missing a
   required field, this step raises an error instead of silently
   accepting bad data.
"""

import argparse
import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

try:
    from secret_key import GROQ_API_KEY
except ImportError:
    GROQ_API_KEY = None

if not GROQ_API_KEY or "your-groq-key-here" in GROQ_API_KEY:
    raise SystemExit("Add your real Groq key to secret_key.py first.")

MODEL_NAME = "llama-3.3-70b-versatile"


# ---------------------------------------------------------------------------
# The strict schema we want back from the model
# ---------------------------------------------------------------------------
class Recipe(BaseModel):
    name: str = Field(description="The name of the dish")
    ingredients: list[str] = Field(
        description="List of ingredients, each with quantity, e.g. '2 cups flour'"
    )
    steps: list[str] = Field(
        description="Ordered list of preparation steps"
    )


def build_chain():
    parser = PydanticOutputParser(pydantic_object=Recipe)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a recipe generator. Always respond with valid JSON "
                "that matches the schema exactly. Do not include any text "
                "outside the JSON object.\n\n{format_instructions}",
            ),
            ("human", "Give me a recipe for: {dish}"),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    model = ChatGroq(model=MODEL_NAME, api_key=GROQ_API_KEY, temperature=0)

    # prompt | model | parser  — same LCEL pattern as before, but this time
    # the last link (PydanticOutputParser) validates and converts the raw
    # text into a real Recipe object, not just a plain string.
    chain = prompt | model | parser
    return chain


def get_recipe(dish: str) -> Recipe:
    chain = build_chain()
    return chain.invoke({"dish": dish})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a strict-JSON recipe")
    parser.add_argument("--dish", help="What dish to generate a recipe for")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dish = args.dish or input("What dish would you like a recipe for? ").strip()

    print(f"\nGenerating recipe for '{dish}'...\n")
    recipe = get_recipe(dish)  # this is a validated Recipe object, not raw text

    print("=== Parsed Pydantic object ===")
    print(f"name: {recipe.name}")
    print(f"ingredients: {recipe.ingredients}")
    print(f"steps: {recipe.steps}")

    print("\n=== Strict JSON ===")
    print(json.dumps(recipe.model_dump(), indent=2))


if __name__ == "__main__":
    main()