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

## Logging & Error Handling
Har request aur error `weather_chatbot.log` file mein Python ke
`logging` module se save hoti hai (app run karne wali directory mein
banti hai). Yeh file `.gitignore` mein hai, is liye git mein commit
nahi hogi.

Log mein yeh cheezein record hoti hain:
- Har OpenWeatherMap request/response (city, status)
- Har Groq LLM request/response (model, city, success/failure)
- Koi bhi error (invalid city, network issue, invalid API key, LLM
  failure, ya koi anjaani exception)

Example log entries:
```
2026-07-31 10:15:02 | INFO     | REQUEST -> OpenWeatherMap: city='Lahore', units='metric'
2026-07-31 10:15:03 | INFO     | RESPONSE <- OpenWeatherMap: success for city='Lahore' (status 200)
2026-07-31 10:15:03 | INFO     | REQUEST -> Groq LLM: model='llama-3.3-70b-versatile', city='Lahore'
2026-07-31 10:15:04 | INFO     | RESPONSE <- Groq LLM: success (312 chars)
2026-07-31 10:16:10 | WARNING  | City not found: 'Lahoreee'
2026-07-31 10:17:45 | ERROR    | OpenWeatherMap connection error for city='Karachi': ...
```

Har API call (`fetch_weather` aur `generate_friendly_response`) apne
try/except blocks mein wrapped hai:
- **Known errors** (invalid city, timeout, connection issue, invalid
  API key, LLM failure) → user ko ek clear, friendly Urdu/English
  message milta hai, aur app chalta rehta hai (crash nahi hota).
- **Anjaani/unexpected errors** → log file mein detail save hoti hai,
  user ko generic "dobara koshish karein" jawab milta hai, aur app
  crash nahi hota.
- Agar koi truly fatal, unhandled error ho jaye, to app gracefully
  exit karta hai aur user ko batata hai ke details log file mein
  dekhein — bina raw Python traceback dikhaye.
