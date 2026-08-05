"""
Weather Chatbot
================
Yeh chatbot user se city ka naam leta hai, OpenWeatherMap API se live
weather data fetch karta hai, aur phir LLM (Groq - Llama 3.3 70B) ke
zariye us raw data ko ek friendly, conversational jawab mein convert
karke print karta hai.

Har request aur error `weather_chatbot.log` file mein Python logging
module se save hoti hai, aur har API call try/except mein wrapped hai
taake koi bhi failure app ko crash na kare — user ko hamesha ek
graceful, friendly error message milega.

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
import logging
import requests
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
LOG_FILE = "weather_chatbot.log"


# ---------------------------------------------------------------------------
# 0. Logging setup — har request/error ek log file mein save hogi
# ---------------------------------------------------------------------------
logger = logging.getLogger("weather_chatbot")
logger.setLevel(logging.INFO)

_formatter = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
_file_handler.setLevel(logging.INFO)      # file mein sab kuch (INFO+) save hoga
_file_handler.setFormatter(_formatter)

_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.WARNING)  # console par sirf warnings/errors
_console_handler.setFormatter(_formatter)

logger.addHandler(_file_handler)
logger.addHandler(_console_handler)
logger.propagate = False  # root logger ko duplicate messages na jayein


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
    logger.info(f"REQUEST -> OpenWeatherMap: city='{city}', units='{units}'")

    try:
        response = requests.get(OPENWEATHER_URL, params=params, timeout=10)
    except requests.exceptions.Timeout:
        logger.error(f"OpenWeatherMap request timed out for city='{city}'")
        raise ConnectionError(
            "Weather service timeout ho gaya. Thodi dair baad dobara koshish karein."
        )
    except requests.exceptions.ConnectionError as exc:
        logger.error(f"OpenWeatherMap connection error for city='{city}': {exc}")
        raise ConnectionError(
            "Internet ya weather service se connect nahi ho pa raha. "
            "Apna connection check karein."
        )

    if response.status_code == 404:
        logger.warning(f"City not found: '{city}'")
        raise ValueError(f"City '{city}' nahi mila. Sahi spelling check karein.")

    if response.status_code == 401:
        logger.error("OpenWeatherMap returned 401 Unauthorized — invalid API key.")
        raise PermissionError(
            "Weather API key invalid ya expired lag rahi hai. "
            ".env file mein OPENWEATHER_API_KEY check karein."
        )

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        logger.error(f"OpenWeatherMap HTTP error for city='{city}': {exc}")
        raise ConnectionError(
            f"Weather service se error mila (status {response.status_code}). "
            "Thodi dair baad dobara koshish karein."
        )

    logger.info(f"RESPONSE <- OpenWeatherMap: success for city='{city}' (status {response.status_code})")
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
    logger.info(f"REQUEST -> Groq LLM: model='{model}', city='{weather_summary.get('city')}'")
    try:
        prompt = WEATHER_PROMPT.format(data=weather_summary)
        response = client.chat.completions.create(
            model=model,
            max_tokens=200,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}],
        )
        reply = response.choices[0].message.content.strip()
        logger.info(f"RESPONSE <- Groq LLM: success ({len(reply)} chars)")
        return reply
    except Exception as exc:
        logger.error(f"Groq LLM call failed: {exc}")
        raise RuntimeError(
            "LLM se friendly jawab generate nahi ho saka. "
            "Thodi dair baad dobara koshish karein."
        )


# ---------------------------------------------------------------------------
# 3. Chatbot loop
# ---------------------------------------------------------------------------
def main():
    weather_api_key = os.environ.get("OPENWEATHER_API_KEY")
    groq_api_key = os.environ.get("GROQ_API_KEY")
    groq_model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

    if not weather_api_key:
        logger.critical("OPENWEATHER_API_KEY not set — app cannot start.")
        print("ERROR: OPENWEATHER_API_KEY not set. Copy .env.example to .env and fill it in.")
        sys.exit(1)
    if not groq_api_key:
        logger.critical("GROQ_API_KEY not set — app cannot start.")
        print("ERROR: GROQ_API_KEY not set. Copy .env.example to .env and fill it in.")
        sys.exit(1)

    try:
        client = Groq(api_key=groq_api_key)
    except Exception as exc:
        logger.critical(f"Failed to initialize Groq client: {exc}")
        print("Chatbot: Groq client initialize nahi ho saka. API key check karein.")
        sys.exit(1)

    logger.info("=== Weather Chatbot session started ===")

    print("=" * 60)
    print(" 🌤️  Weather Chatbot — apna sheher likhein (ya 'exit' likhein)")
    print(f"    (Har request/error '{LOG_FILE}' mein save ho rahi hai)")
    print("=" * 60)

    while True:
        try:
            city = input("\nCity ka naam: ").strip()
        except (EOFError, KeyboardInterrupt):
            logger.info("Session ended by user (EOF/KeyboardInterrupt).")
            print("\nChatbot: Allah Hafiz! 👋")
            break

        if not city:
            print("Kuch to likhein!")
            continue
        if city.lower() in ("exit", "quit", "bye"):
            logger.info("=== Weather Chatbot session ended by user ===")
            print("Chatbot: Allah Hafiz! 👋")
            break

        # ------------------------------------------------------------
        # Step 1: Weather data fetch karna (graceful error handling)
        # ------------------------------------------------------------
        try:
            raw_data = fetch_weather(city, weather_api_key)
        except ValueError as ve:
            print(f"Chatbot: {ve}")
            continue
        except (ConnectionError, PermissionError) as known_err:
            print(f"Chatbot: {known_err}")
            continue
        except Exception as exc:
            # Koi bhi anticipate na kiya gaya error — app crash nahi hoga
            logger.error(f"Unexpected error while fetching weather for '{city}': {exc}")
            print("Chatbot: Kuch anjaani wajah se weather data nahi mil saka. "
                  "Thodi dair baad dobara koshish karein.")
            continue

        summary = extract_summary(raw_data)

        # ------------------------------------------------------------
        # Step 2: LLM se friendly response generate karna
        # ------------------------------------------------------------
        try:
            reply = generate_friendly_response(client, groq_model, summary)
        except RuntimeError as re_err:
            print(f"Chatbot: {re_err}")
            continue
        except Exception as exc:
            logger.error(f"Unexpected error while generating LLM response: {exc}")
            print("Chatbot: Kuch anjaani wajah se jawab generate nahi ho saka. "
                  "Thodi dair baad dobara koshish karein.")
            continue

        print(f"\nChatbot: {reply}")


if __name__ == "__main__":
    try:
        main()
    except Exception as fatal_exc:
        logger.critical(f"Unhandled fatal error, app is exiting: {fatal_exc}")
        print("Chatbot: Ek unexpected error ki wajah se app band ho rahi hai. "
              f"Details '{LOG_FILE}' file mein hain.")
        sys.exit(1)
