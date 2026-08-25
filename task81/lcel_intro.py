"""
LangChain Expression Language (LCEL) intro.

Part 1 shows a "standard" call to a chat model, the old/manual way.
Part 2 rebuilds the exact same thing as an LCEL chain using the
`prompt | model | output_parser` pipe syntax, and explains what each
piece (a "Runnable") does.

Uses ChatGroq so it runs on the free Groq API key already set up in
secret_key.py. Swap in ChatOpenAI the same way if you want to use OpenAI
instead (see the commented-out block below).
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq

try:
    from secret_key import GROQ_API_KEY
except ImportError:
    GROQ_API_KEY = None

if not GROQ_API_KEY or "your-groq-key-here" in GROQ_API_KEY:
    raise SystemExit("Add your real Groq key to secret_key.py first.")

MODEL_NAME = "llama-3.3-70b-versatile"


# ---------------------------------------------------------------------------
# PART 1: Standard call — build the model, call it directly, no chain
# ---------------------------------------------------------------------------
def standard_call(topic: str) -> str:
    model = ChatGroq(model=MODEL_NAME, api_key=GROQ_API_KEY)
    prompt_text = f"Explain {topic} in exactly 2 short sentences."
    response = model.invoke(prompt_text)   # returns an AIMessage object
    return response.content                # you have to manually pull out .content


# ---------------------------------------------------------------------------
# PART 2: The same thing, rebuilt as an LCEL chain
#
# Every piece here (prompt, model, output_parser) is a "Runnable" — an
# object with a shared .invoke() / .stream() / .batch() interface. The `|`
# pipe operator wires them together so the output of one becomes the input
# of the next, just like a Unix pipe:
#
#   ChatPromptTemplate  ->  formats your variables into chat messages
#   ChatGroq (the model)  ->  takes those messages, returns an AIMessage
#   StrOutputParser  ->  extracts the plain string from the AIMessage
# ---------------------------------------------------------------------------
def build_lcel_chain():
    prompt = ChatPromptTemplate.from_template(
        "Explain {topic} in exactly 2 short sentences."
    )
    model = ChatGroq(model=MODEL_NAME, api_key=GROQ_API_KEY)
    output_parser = StrOutputParser()

    chain = prompt | model | output_parser
    return chain


# --- If you want to use OpenAI instead of Groq, swap ChatGroq for this: ---
# from langchain_openai import ChatOpenAI
# model = ChatOpenAI(model="gpt-4o-mini", api_key=OPENAI_API_KEY)
# everything else (prompt, output_parser, the | pipe) stays identical —
# that's the whole point of the Runnable interface: components are
# interchangeable as long as they speak the same protocol.


if __name__ == "__main__":
    topic = "recursion"

    print("=== Standard call ===")
    print(standard_call(topic))

    print("\n=== LCEL chain (prompt | model | output_parser) ===")
    chain = build_lcel_chain()
    result = chain.invoke({"topic": topic})   # dict in, plain string out
    print(result)

    print("\n=== LCEL chain, streamed ===")
    for chunk in chain.stream({"topic": "closures in Python"}):
        print(chunk, end="", flush=True)
    print()