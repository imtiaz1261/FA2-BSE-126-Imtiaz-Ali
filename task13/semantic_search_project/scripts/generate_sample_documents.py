"""
generate_sample_documents.py
-----------------------------
Utility script that generates 100 sample .txt documents spread across
10 topic categories. These are used to demonstrate and test the
Semantic Search Engine end to end.

Each document includes a small metadata header (category, doc_id) so
the project can also demonstrate metadata filtering.

Run:
    python scripts/generate_sample_documents.py
"""

import os
import random

random.seed(42)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "documents")

# Topic -> list of (title, body) seed sentences. We combine / vary these
# to produce 10 unique-ish documents per topic (100 total).
TOPICS = {
    "technology": {
        "keywords": ["artificial intelligence", "cloud computing", "cybersecurity",
                     "software engineering", "5G networks", "quantum computing",
                     "blockchain", "robotics", "edge computing", "open source software"],
        "template": (
            "{kw} is reshaping how modern businesses operate. Engineers and "
            "researchers are investing heavily in {kw} to improve efficiency, "
            "scalability, and reliability of digital systems. Companies adopting "
            "{kw} report faster development cycles and improved customer "
            "experiences. Experts predict that {kw} will continue to be a major "
            "driver of innovation over the next decade, influencing everything "
            "from data centers to consumer devices."
        ),
    },
    "health": {
        "keywords": ["cardiovascular health", "mental wellness", "nutrition science",
                     "sleep hygiene", "physical therapy", "vaccination programs",
                     "chronic disease management", "preventive medicine",
                     "telemedicine", "public health policy"],
        "template": (
            "Recent studies on {kw} highlight the importance of early intervention "
            "and consistent lifestyle habits. Doctors recommend that patients pay "
            "closer attention to {kw} as part of a holistic approach to wellbeing. "
            "Advances in {kw} have made it easier for healthcare providers to "
            "deliver personalized care. Public health experts continue to stress "
            "that {kw} should be a shared responsibility between individuals, "
            "communities, and policymakers."
        ),
    },
    "finance": {
        "keywords": ["stock market volatility", "personal budgeting", "cryptocurrency",
                     "retirement planning", "inflation trends", "venture capital",
                     "corporate taxation", "mortgage rates", "investment diversification",
                     "central bank policy"],
        "template": (
            "Financial analysts are closely watching {kw} as it shapes decisions "
            "for both individual investors and large institutions. Understanding "
            "{kw} helps consumers make informed choices about saving and spending. "
            "In recent years, {kw} has become a frequent topic in economic "
            "forecasts and policy debates. Experts advise diversifying strategies "
            "to manage the risks associated with {kw}."
        ),
    },
    "sports": {
        "keywords": ["football tactics", "marathon training", "basketball analytics",
                     "Olympic preparation", "cricket strategy", "tennis technique",
                     "sports psychology", "youth athletics programs",
                     "esports competitions", "swimming performance"],
        "template": (
            "Coaches and athletes are increasingly turning to data-driven methods "
            "to improve {kw}. The evolution of {kw} over the last decade shows how "
            "training methods have modernized. Fans and analysts alike are "
            "fascinated by how {kw} influences match outcomes and career "
            "longevity. Sports scientists continue to research {kw} to help "
            "athletes reach peak performance safely."
        ),
    },
    "travel": {
        "keywords": ["backpacking through Southeast Asia", "sustainable tourism",
                     "road trip itineraries", "budget airline travel",
                     "mountain trekking", "cultural heritage sites",
                     "island hopping vacations", "solo travel safety",
                     "culinary tourism", "eco-lodging"],
        "template": (
            "Travelers exploring {kw} often seek authentic experiences that go "
            "beyond typical tourist attractions. Guides on {kw} emphasize the "
            "importance of planning ahead while staying open to spontaneous "
            "adventures. Bloggers who cover {kw} share tips on budgeting, packing, "
            "and navigating local customs. Interest in {kw} has grown steadily as "
            "more people prioritize memorable experiences over material "
            "possessions."
        ),
    },
    "education": {
        "keywords": ["online learning platforms", "STEM education", "early childhood literacy",
                     "student mental health", "vocational training",
                     "university admissions", "special education support",
                     "language immersion programs", "classroom technology",
                     "lifelong learning"],
        "template": (
            "Educators are rethinking {kw} to better serve students in a rapidly "
            "changing world. Research on {kw} suggests that engagement and "
            "accessibility are key factors for success. Schools implementing new "
            "approaches to {kw} report measurable improvements in student "
            "outcomes. Policymakers continue to debate how to fund and scale {kw} "
            "effectively across diverse communities."
        ),
    },
    "environment": {
        "keywords": ["renewable energy adoption", "climate change mitigation",
                     "plastic waste reduction", "biodiversity conservation",
                     "sustainable agriculture", "carbon capture technology",
                     "deforestation prevention", "water resource management",
                     "urban green spaces", "electric vehicle infrastructure"],
        "template": (
            "Scientists and policymakers are prioritizing {kw} to address "
            "pressing environmental challenges. Communities investing in {kw} "
            "often see long-term benefits for both ecosystems and local "
            "economies. Reports on {kw} indicate growing public support for "
            "stronger environmental protections. Innovators continue to develop "
            "new solutions related to {kw} to build a more sustainable future."
        ),
    },
    "food": {
        "keywords": ["plant-based diets", "artisanal baking", "fermentation techniques",
                     "farm-to-table dining", "street food culture",
                     "molecular gastronomy", "coffee roasting", "wine pairing",
                     "food preservation methods", "regional cuisine traditions"],
        "template": (
            "Chefs experimenting with {kw} are redefining what modern dining looks "
            "like. Home cooks interested in {kw} often start with simple recipes "
            "before mastering advanced techniques. Food critics have noted a "
            "growing appreciation for {kw} in restaurants around the world. "
            "Cultural historians point out that {kw} reflects deep traditions "
            "passed down through generations."
        ),
    },
    "science": {
        "keywords": ["space exploration", "genetic engineering", "particle physics",
                     "neuroscience research", "renewable materials science",
                     "astrobiology", "climate modeling", "marine biology",
                     "nanotechnology", "evolutionary biology"],
        "template": (
            "Recent breakthroughs in {kw} are expanding our understanding of the "
            "natural world. Research teams working on {kw} rely on collaboration "
            "across multiple disciplines. Funding agencies have increased support "
            "for {kw} due to its potential long-term impact. Public interest in "
            "{kw} continues to grow as new discoveries make headlines worldwide."
        ),
    },
    "business": {
        "keywords": ["remote work culture", "supply chain management", "startup fundraising",
                     "digital marketing strategy", "customer experience design",
                     "corporate leadership development", "e-commerce growth",
                     "mergers and acquisitions", "small business resilience",
                     "workplace diversity initiatives"],
        "template": (
            "Companies navigating {kw} are adapting their strategies to stay "
            "competitive in a fast-changing market. Executives who prioritize "
            "{kw} often see stronger long-term growth and employee satisfaction. "
            "Consultants specializing in {kw} help organizations identify "
            "inefficiencies and new opportunities. Industry reports show that "
            "{kw} will remain a top priority for business leaders in the coming "
            "years."
        ),
    },
}


def build_documents():
    docs = []
    doc_id = 1
    for category, info in TOPICS.items():
        for kw in info["keywords"]:
            title = kw.title()
            body = info["template"].format(kw=kw)
            docs.append(
                {
                    "doc_id": doc_id,
                    "category": category,
                    "title": title,
                    "body": body,
                }
            )
            doc_id += 1
    return docs


def write_documents(docs, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for doc in docs:
        filename = f"doc_{doc['doc_id']:03d}.txt"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"Title: {doc['title']}\n")
            f.write(f"Category: {doc['category']}\n")
            f.write("\n")
            f.write(doc["body"])
            f.write("\n")
    print(f"Wrote {len(docs)} documents to {os.path.abspath(output_dir)}")


if __name__ == "__main__":
    documents = build_documents()
    assert len(documents) == 100, f"Expected 100 documents, got {len(documents)}"
    write_documents(documents, OUTPUT_DIR)
