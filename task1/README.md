# Async API Fetcher (Simulating Async LLM Calls)

Ek async Python script jo `aiohttp` use kar ke ek dummy API (JSONPlaceholder) se **multiple
requests concurrently** (ek sath) fetch karti hai — real-world scenario simulate karne ke liye
jahan multiple LLM API calls ek sath bheji jati hain taake total time kam ho.

---

## Requirements

- Python 3.8+
- `aiohttp` library

---

## Installation

Terminal (ya VS Code terminal) mein ye command chalao:

```bash
python -m pip install aiohttp
```

Agar `pip` command directly kaam na kare, `python -m pip` use karo (upar wala command).

---

## Usage

Script run karne ke liye:

```bash
python project1.py
```

---

## What This Script Does

1. Teen dummy API URLs (JSONPlaceholder) ki list banayi gayi hai.
2. Har URL ke liye ek `asyncio.Task` banaya jata hai — matlab teeno requests **ek sath**
   (concurrently) bheji jati hain, ek ke complete hone ka wait nahi karte.
3. `asyncio.gather()` se sab tasks ka result ek sath collect kiya jata hai.
4. Total time measure kiya jata hai taake concurrency ka fayda dikh sake.

---
<img width="461" height="262" alt="Screenshot 2026-07-07 161329" src="https://github.com/user-attachments/assets/3ac50fcb-545d-4729-a3a3-1860663a0536" />

## Output Example

```
Sending request to https://jsonplaceholder.typicode.com/posts/1 ...
Sending request to https://jsonplaceholder.typicode.com/posts/2 ...
Sending request to https://jsonplaceholder.typicode.com/posts/3 ...
Done with https://jsonplaceholder.typicode.com/posts/1
Done with https://jsonplaceholder.typicode.com/posts/2
Done with https://jsonplaceholder.typicode.com/posts/3

--- Results ---
Title: sunt aut facere repellat provident occaecati excepturi optio reprehenderit
Title: qui est esse
Title: ea molestias quasi exercitationem repellat qui ipsa sit aut

Finished in 0.XX seconds
```

Notice karo — teeno "Sending request" lines pehle print hoti hain (kyunki sab ek sath start
hui thi), phir "Done" lines aati hain jab har request complete hoti hai. Ye concurrency ka
proof hai — agar sequential (ek ek karke) hota, to time zyada lagta.

---

## How It Works

| Part | Kaam |
|---|---|
| `fetch_data()` | Ek single async request bhejta hai aur JSON response return karta hai |
| `asyncio.create_task()` | Har request ko background mein turant start kar deta hai (concurrently) |
| `asyncio.gather()` | Sab tasks ka result ek sath, order mein collect karta hai |
| `aiohttp.ClientSession()` | Connection reuse karta hai taake multiple requests efficient tareeqe se bheji ja sakein |

---

## Real API se Connect Karna (Optional / Future Step)

Abhi ye script free, dummy API (JSONPlaceholder) use kar rahi hai — koi API key ya billing
ki zaroorat nahi. Agar future mein real LLM API (jese Claude ya OpenAI) use karni ho, to
`URLS` list ki jagah real API endpoints aur authentication headers add karne honge.

---

## Project Structure

```
task1/
├── project1.py     # Main script
└── README.md        # Ye file
```
