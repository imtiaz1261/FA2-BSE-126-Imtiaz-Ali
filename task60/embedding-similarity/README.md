# Sentence embeddings — cosine similarity explorer

Ek self-contained tool: apne sentences daalein, real semantic embeddings generate karein (poori tarah browser mein, koi API key ki zaroorat nahi), aur dekhein ki semantically similar sentences ke embeddings kitne "close" hote hain — ek similarity matrix (heatmap), top/bottom pairs, aur ek 2D visualization ke through.

## Kaise chalayein

1. `index.html` ko kisi bhi modern browser mein kholein (Chrome/Edge/Firefox — internet connection chahiye pehli baar model download karne ke liye).
2. Textarea mein apne sentences likhein — ek line mein ek sentence (2 se 20 sentences).
3. "Generate embeddings + compare" par click karein.
4. Pehli baar chalane par ek chhota (~25MB) embedding model browser mein download hoga; uske baad sab kuch local chalega.

## Kya-kya dikhta hai

1. **Cosine similarity matrix** — har sentence-pair ke beech ek 0 se 1 tak ka similarity score, color-coded heatmap ke roop mein (1.0 = same direction/meaning, 0 = unrelated).
2. **Most/least similar pairs** — top 3 sabse zyada aur sabse kam similar jode, taaki pattern turant nazar aaye.
3. **2D projection** — classical multidimensional scaling (MDS) se saare sentences ka ek 2D layout, jisme semantically close sentences visually bhi paas-paas dikhte hain.

## Kaise kaam karta hai (technical)

- **Embeddings**: `transformers.js` (Xenova) library `Xenova/all-MiniLM-L6-v2` model load karti hai — yeh wahi family hai jo Sentence-Transformers mein use hoti hai, 384-dimensional normalized vectors deta hai. Sab kuch browser ke andar (WASM) chalta hai — koi data server ko nahi jaata, isliye koi API key bhi nahi chahiye.
- **Cosine similarity**: chunki vectors already normalized hain, cosine similarity sirf dot product hai: `sim(a,b) = a · b`.
- **2D projection**: similarity scores se distance nikaal kar (`d = sqrt(2 - 2*sim)`), classical MDS apply kiya jata hai — double-centering ke baad ek chhoti symmetric matrix ka eigen-decomposition (Jacobi algorithm, hand-implemented, koi extra library nahi) top-2 components deta hai jo plot ban jate hain.

## Limitations

- 20 se zyada sentences par visualization clutter ho sakta hai — is limit ko `index.html` mein badla ja sakta hai.
- 2D projection ek approximation hai; asli embeddings 384-dimensional hote hain, isliye kabhi-kabhi 2D mein do sentences jitne close dikhte hain, high-dimensional similarity utni exact nahi hoti — asli numbers ke liye hamesha similarity matrix table dekhein.
- Model English-optimized hai; Hindi/Urdu jaise languages ke liye similarity kaam to karega lekin utna precise nahi hoga jitna English sentences ke liye.
