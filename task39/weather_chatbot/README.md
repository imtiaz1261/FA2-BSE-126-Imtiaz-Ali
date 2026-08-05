# Weather Chatbot (OpenWeatherMap + Groq LLM)

Yeh chatbot user se **city ka naam** leta hai, **OpenWeatherMap API** se
live weather data fetch karta hai, aur phir **Groq LLM** (`llama-3.3-70b-versatile`)
ke zariye us raw data ko ek **friendly, conversational jawab** mein
convert karke print karta hai.

## Project Structure
```
weather_chatbot/
├── main.py             # Main chatbot loop (fetch weather + LLM response)
├── requirements.txt     # Python dependencies
├── .env.example         # Sample env file (copy this to .env)
├── .gitignore           # Ensures .env never gets committed
└── README.md            # Yeh file
```

## Setup Instructions

### 1. Project extract karein
```bash
unzip weather_chatbot.zip
cd weather_chatbot
```

### 2. (Optional) Virtual environment banayein
```bash
python -m venv venv
source venv/bin/activate      # Mac/Linux
venv\Scripts\activate         # Windows
```

### 3. Dependencies install karein
```bash
pip install -r requirements.txt
```

### 4. API keys set karein
```bash
cp .env.example .env
```
`.env` file open karke apni keys daalein:
```
OPENWEATHER_API_KEY=your-openweathermap-key-here
GROQ_API_KEY=your-groq-api-key-here
GROQ_MODEL=llama-3.3-70b-versatile
```

**Zaroori:** `.env` ko kabhi git mein commit na karein (already
`.gitignore` mein hai). Agar koi key kahin publicly share ho chuki ho,
turant us provider ke dashboard se regenerate kar dein.

### 5. Chatbot run karein
```bash
python main.py
```

## Example Session
```
🌤️  Weather Chatbot — apna sheher likhein (ya 'exit' likhein)

City ka naam: Lahore

Chatbot: Right now Lahore is sitting at a warm 34°C, though it feels
more like 37°C with the humidity — so it's a proper hot one today!
Skies are mostly clear, so grab some water and maybe skip the midday
sun if you can. 😊

City ka naam: exit
Chatbot: Allah Hafiz! 👋
```

## Notes
- Temperature default mein **Celsius (metric units)** mein aati hai —
  `main.py` ke `fetch_weather()` function mein `units="metric"` change
  karke Fahrenheit (`imperial`) ya Kelvin (`standard`) bhi kar sakte hain.
- Agar city ka naam galat ho ya na mile, chatbot aik friendly error
  message dega aur dobara city puchega.
- `WEATHER_PROMPT` ko `main.py` mein edit karke reply ka tone/style
  (e.g. more formal, more detailed, different language) tweak kar
  sakte hain.
