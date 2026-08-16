# Semantic Search Engine (Meaning-based, not Keyword-based)

Yeh ek chhota, self-contained semantic search engine hai jo aapke dataset
(default: 100+ product descriptions) par **meaning ke hisaab se** results
deta hai — keyword ke exact match par nahi. Matlab query
`"warm winter clothing"` bhi `"puffer jacket with synthetic insulation"`
ko top result de sakta hai, chahe ek bhi shabd match na ho.

## Kaise kaam karta hai

- Har product description ko **TF-IDF + Latent Semantic Analysis (LSA)**
  se ek vector me convert kiya jaata hai. LSA un words ko "connect"
  kar deta hai jo similar context me use hote hain (jaise "warm",
  "jacket", "winter", "insulation"), isliye related meaning wale
  documents match hote hain chahe unke exact words alag ho.
- Query ko bhi usi tarah vectorize karke, **cosine similarity** se
  sabse "close-in-meaning" results nikale jaate hain.
- Yeh backend **100% offline** chalta hai — koi API key ya internet
  nahi chahiye.
- Optionally, agar aap `pip install sentence-transformers` karke
  `--backend embeddings` use karein, to deep neural embeddings
  (better semantic quality) use hongi — is case me pehli baar model
  download hone ke liye internet chahiye hoga.

## Quick Start

```bash
# 1) Install dependencies
pip install -r requirements.txt

# 2) (Optional) Regenerate the sample dataset
python data/generate_dataset.py

# 3) Try it from the command line
python search_cli.py

# 4) Or run the web UI
python app.py
# then open http://localhost:5000
```

CLI example:
```
search> something to keep me warm in winter
  1. [0.751] Men's Winter Puffer Jacket
     Warm, lightweight jacket filled with synthetic insulation, windproof shell...
  2. [0.583] Wool Blend Winter Scarf
     Soft, cozy scarf that adds warmth and style to any winter outfit...
```

## Apna khud ka dataset use karna (Using your own data)

1. `data/products.csv` ko replace kar dein apni CSV file se, ya
   `--csv path/to/your.csv` pass karein.
2. CSV me kam se kam ek `id` column aur baaki text columns hone chahiye
   (jaise `name`, `description`, `category` — column names kuch bhi ho
   sakte hain).
3. Agar aap chahte hain ki sirf kuch specific columns search me use
   ho, to code me:

   ```python
   engine = SemanticSearchEngine.from_csv(
       "data/my_data.csv",
       text_fields=["title", "description"],  # only these columns are searched
   )
   ```

   Baaki columns (jaise price, image_url) results me dikhenge lekin
   search ranking par asar nahi dalenge.

## Files

```
semantic-search-engine/
├── data/
│   ├── products.csv           # sample dataset (100+ product descriptions)
│   └── generate_dataset.py    # regenerates products.csv
├── semantic_search.py         # core SemanticSearchEngine class
├── search_cli.py              # interactive command-line search
├── app.py                     # Flask web app (search box UI)
├── templates/index.html       # web UI
├── requirements.txt
└── README.md
```

## Using it in your own code

```python
from semantic_search import SemanticSearchEngine

engine = SemanticSearchEngine.from_csv("data/products.csv")

results = engine.search("gift for a toddler", top_k=5)
for r in results:
    print(r.score, r.row["name"])

# Filter to a category while still ranking by meaning
results = engine.search("phone charger", top_k=5, filters={"category": "Electronics"})
```

## Upgrading to deep embeddings (optional, better accuracy)

```bash
pip install sentence-transformers
python search_cli.py --backend embeddings
# or
engine = SemanticSearchEngine.from_csv("data/products.csv", backend="embeddings")
```

This swaps LSA for the `all-MiniLM-L6-v2` sentence-transformer model,
which usually understands paraphrases, synonyms, and typos noticeably
better — worth it once you have internet access to download the model
(~90MB, one-time).

## Notes

- Dataset me jitne zyada products honge, LSA utna behtar "concepts"
  seekhega — 100 products ke liye yeh already achha kaam karta hai,
  aur yeh approach 10,000+ rows tak bhi scale karta hai.
- Agar aapka data bahut technical/niche hai (jaise medical ya legal
  jargon), to `embeddings` backend generally better perform karega
  kyunki wo pretrained pe already bahut context seekh chuka hai.
