import shutil
from code_alpha.spec.generator import SpecGenerator

REPO_ROOT = "demo_repo"
shutil.rmtree(REPO_ROOT, ignore_errors=True)

if __name__ == "__main__":
    gen = SpecGenerator(REPO_ROOT, feature_slug="signup-rate-limit")

    print("== generate_all() ==")
    gen.generate_all(
        feature_request="Add rate limiting to the /signup endpoint",
        repo_context="Existing Flask app in api/, no rate limiting middleware yet.",
    )
    for name, meta in gen.store.manifest.items():
        print(f"  {name}: v{meta['version']} hash={meta['hash']} from={meta['generated_from_hash']}")

    print("\n== sync_status() right after generation (nothing stale) ==")
    print(" ", gen.sync_status())

    print("\n== human hand-edits requirements.md ==")
    edited = gen.store.read_doc("requirements") + "\n\n## Added by human\n- Also rate-limit /login."
    gen.store.write_doc("requirements", edited)
    print(" ", gen.sync_status())

    print("\n== regenerate_from('requirements') ==")
    regenerated = gen.regenerate_from("requirements", repo_context="Existing Flask app in api/.")
    print(f"  regenerated: {regenerated}")
    print(" ", gen.sync_status())

    print(f"\nfiles on disk under {gen.store.dir}:")
    import os
    for root, _, files in os.walk(gen.store.dir):
        for f in files:
            print("  ", os.path.relpath(os.path.join(root, f), gen.store.dir))
