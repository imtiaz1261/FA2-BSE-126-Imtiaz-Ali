"""
app.py
------
A small Flask web app with a search box for the semantic search engine.

Run:
    pip install -r requirements.txt
    python app.py
Then open http://localhost:5000 in your browser.
"""
from pathlib import Path
from flask import Flask, render_template, request, jsonify

from semantic_search import SemanticSearchEngine

app = Flask(__name__)

CSV_PATH = Path(__file__).parent / "data" / "products.csv"
print("Building search index (this runs once at startup)...")
ENGINE = SemanticSearchEngine.from_csv(str(CSV_PATH))
print(f"Ready. Indexed {len(ENGINE.records)} products.")


@app.route("/")
def home():
    return render_template("index.html", count=len(ENGINE.records))


@app.route("/api/search")
def api_search():
    query = request.args.get("q", "")
    top_k = int(request.args.get("top_k", 8))
    category = request.args.get("category") or None

    filters = {"category": category} if category else None
    results = ENGINE.search(query, top_k=top_k, filters=filters)

    return jsonify(
        {
            "query": query,
            "count": len(results),
            "results": [
                {
                    "score": round(r.score, 4),
                    "name": r.row.get("name", ""),
                    "category": r.row.get("category", ""),
                    "description": r.row.get("description", ""),
                }
                for r in results
            ],
        }
    )


@app.route("/api/categories")
def api_categories():
    cats = sorted({r.get("category", "") for r in ENGINE.records if r.get("category")})
    return jsonify(cats)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
