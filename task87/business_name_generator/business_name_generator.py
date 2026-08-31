import re

def generate_names(business_type, niche):
    niche_words = re.findall(r"[A-Za-z]+", niche.lower())
    type_words = re.findall(r"[A-Za-z]+", business_type.lower())
    seed = (niche_words + type_words + ["pure", "fresh", "craft", "urban", "prime", "bloom"])
    words = [w.capitalize() for w in seed if len(w) > 2]

    candidates = [
        (f"{words[0]} & Co.", "Simple, memorable, and flexible enough to grow with the business."),
        (f"{words[0]}Craft", "Blends the niche with a crafted, quality-focused feel."),
        (f"{words[-1]}Nest", "Creates a warm, approachable brand image."),
        (f"{words[0]}Bloom", "Suggests freshness, growth, and positive customer experiences."),
        (f"Pure {words[0]}", "Signals a clean, focused, niche-first brand."),
        (f"{words[0]}House", "Feels established while remaining easy to brand."),
        (f"{words[-1]} & Leaf", "Adds a natural, premium-sounding identity."),
        (f"Urban {words[0]}", "Gives the business a modern, contemporary positioning."),
        (f"{words[0]}Verse", "Feels creative and distinctive without being too narrow."),
        (f"Prime {words[0]}", "Communicates quality and a premium positioning.")
    ]
    return candidates

def main():
    print("Business Name Generator")
    business_type = input("Business type (e.g. organic tea shop): ").strip()
    niche = input("Niche / target audience: ").strip()

    if not business_type or not niche:
        print("Please enter both business type and niche.")
        return

    print("\n10 creative, available-sounding names:")
    for i, (name, reason) in enumerate(generate_names(business_type, niche), 1):
        print(f"{i}. {name} — {reason}")

if __name__ == "__main__":
    main()
