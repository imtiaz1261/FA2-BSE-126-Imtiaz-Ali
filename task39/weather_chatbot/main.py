"""
Weather Chatbot
================
Yeh chatbot user se city ka naam leta hai, OpenWeatherMap API se live
weather data fetch karta hai, aur phir LLM (Groq - Llama 3.3 70B) ke
zariye us raw data ko ek friendly, conversational jawab mein convert
karke print karta hai.

Setup:
    1. `.env.example` ko `.env` mein copy karein aur apni API keys daalein:
        OPENWEATHER_API_KEY=your-openweathermap-key
        GROQ_API_KEY=your-groq-key
        GROQ_MODEL=llama-3.3-70b-versatile

Run:
    python main.py
"""

import os
import sys
import requests
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


# ---------------------------------------------------------------------------
# 1. OpenWeatherMap se raw weather data fetch karna
# ---------------------------------------------------------------------------
def fetch_weather(city: str, api_key: str, units: str = "metric") -> dict:
    """City ka naam le kar OpenWeatherMap se current weather return karta hai."""
    params = {
        "q": city,
        "appid": api_key,
        "units": units,  # metric = Celsius
    }
    response = requests.get(OPENWEATHER_URL, params=params, timeout=10)

    if response.status_code == 404:
        raise ValueError(f"City '{city}' nahi mila. Sahi spelling check karein.")
    response.raise_for_status()

    return response.json()


def extract_summary(raw_data: dict) -> dict:
    """API response se sirf zaroori fields nikalta hai (LLM ko dene ke liye)."""
    return {
        "city": raw_data.get("name"),
        "country": raw_data.get("sys", {}).get("country"),
        "temperature_c": raw_data.get("main", {}).get("temp"),
        "feels_like_c": raw_data.get("main", {}).get("feels_like"),
        "humidity_percent": raw_data.get("main", {}).get("humidity"),
        "condition": raw_data.get("weather", [{}])[0].get("description"),
        "wind_speed_mps": raw_data.get("wind", {}).get("speed"),
    }


# ---------------------------------------------------------------------------
# 2. LLM prompt — raw weather data ko friendly jawab mein convert karna
# ---------------------------------------------------------------------------
WEATHER_PROMPT = """You are a friendly weather assistant chatbot.

Convert the following raw weather data into a short, warm, conversational
reply for the user (2-4 sentences). Mention the temperature, how it feels,
general condition, and give a small practical tip (e.g. carry an umbrella,
wear a jacket, stay hydrated) if relevant. Do not just list the numbers
robotically — sound natural and human, like you're chatting with a friend.

Weather Data (JSON):
{data}

Friendly Reply:"""


def generate_friendly_response(client: Groq, model: str, weather_summary: dict) -> str:
    prompt = WEATHER_PROMPT.format(data=weather_summary)
    response = client.chat.completions.create(
        model=model,
        max_tokens=200,
        temperature=0.7,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# 3. Chatbot loop
# ---------------------------------------------------------------------------
def main():
    weather_api_key = os.environ.get("OPENWEATHER_API_KEY")
    groq_api_key = os.environ.get("GROQ_API_KEY")
    groq_model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

    if not weather_api_key:
        print("ERROR: OPENWEATHER_API_KEY not set. Copy .env.example to .env and fill it in.")
        sys.exit(1)
    if not groq_api_key:
        print("ERROR: GROQ_API_KEY not set. Copy .env.example to .env and fill it in.")
        sys.exit(1)

    client = Groq(api_key=groq_api_key)

    print("=" * 60)
    print(" 🌤️  Weather Chatbot — apna sheher likhein (ya 'exit' likhein)")
    print("=" * 60)

    while True:
        city = input("\nCity ka naam: ").strip()
        if not city:
            print("Kuch to likhein!")
            continue
        if city.lower() in ("exit", "quit", "bye"):
            print("Chatbot: Allah Hafiz! 👋")
            break

        try:
            raw_data = fetch_weather(city, weather_api_key)
        except ValueError as ve:
            print(f"Chatbot: {ve}")
            continue
        except requests.exceptions.RequestException as re:
            print(f"Chatbot: Weather data fetch karne mein masla hua: {re}")
            continue

        summary = extract_summary(raw_data)

        try:
            reply = generate_friendly_response(client, groq_model, summary)
        except Exception as exc:
            print(f"Chatbot: LLM se jawab generate karne mein masla hua: {exc}")
            continue

        print(f"\nChatbot: {reply}")


if __name__ == "__main__":
    main()
