# PDF RAG assistant — 3D upload page + Groq-powered answers

Ek self-contained web app: 3D animated background wala upload page, PDF par real retrieval-augmented generation (RAG) pipeline, aur Groq ke fast LLM se page-cited jawaab.

## Zaroori: apni API key ke baare mein

Aapne pehle is chat mein ek Groq API key plain text mein bheji thi. Chat mein bheja gaya koi bhi secret ab "private" nahi raha, isliye maine woh key kisi bhi file mein nahi daali. **Please console.groq.com par jaakar woh purani key revoke/regenerate kar dein**, aur ek nayi key banayein sirf apne local use ke liye.

## Setup

1. `config.js` file kholein (kisi bhi text editor mein).
2. Is line mein apni nayi Groq key paste karein:
   ```js
   window.GROQ_API_KEY = "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";
   ```
3. File save karein.
4. `index.html` ko browser mein kholein.

Agar browser security ki wajah se local files (`file://`) se `config.js` load nahi hota, to folder ke andar simple local server chalayein aur `http://localhost:8000` par kholein:
```
python3 -m http.server 8000
```

## Yeh RAG kaise kaam karta hai

1. **Extraction** — `pdf.js` browser mein hi har page ka text nikalta hai.
2. **Chunking** — har page ka text ~700-character overlapping chunks mein toda jata hai, har chunk apne page number ke saath tagged hota hai.
3. **Indexing** — har chunk ke liye TF-IDF vector banaya jata hai (poore document ke vocabulary ke against).
4. **Retrieval** — sawaal poochhne par, sawaal ka bhi TF-IDF vector banaya jata hai aur cosine similarity se sabse relevant 8 chunks chune jaate hain — poora document nahi bheja jata.
5. **Generation** — sirf woh retrieved chunks + sawaal Groq ke `openai/gpt-oss-120b` model ko bheje jaate hain, is instruction ke saath ki jawaab sirf diye gaye content se banaye aur har fact ke baad `[p.N]` likhe.
6. UI un `[p.N]` markers ko clickable badges mein badal deti hai — click karne par woh page turant preview ho jata hai.

## Security notes

- `config.js` mein hi aapki key rehti hai — yeh sirf aapke browser se seedha Groq ke server ko jaati hai, kahin aur nahi.
- Is folder ko kabhi bhi public repo, screenshot, ya kisi aur ke saath share na karein jab tak `config.js` khali (ya redacted) na ho.
- Agar yeh app kisi shared/deployed website par daalni ho (sirf aap use nahi karenge), to key ko client-side JS mein rakhna surakshit nahi hai — us case mein ek chhota backend proxy banayein jo key server-side rakhe.

## Limitations

- Scanned/image-only PDFs mein text layer na ho to extraction khaali aa sakta hai (OCR shamil nahi hai).
- TF-IDF ek lightweight, keyword-based retrieval hai — dense/neural embeddings jitna semantic match nahi karta, lekin bina external embedding service ke, purely browser mein chalne wala hai.
