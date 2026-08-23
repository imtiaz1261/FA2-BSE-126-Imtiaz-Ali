import os

IGNORE_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv", "dist", "build"}

EXT_LANG = {
    ".py": "python", ".js": "javascript", ".ts": "typescript", ".tsx": "typescript",
    ".jsx": "javascript", ".go": "go", ".rs": "rust", ".java": "java", ".rb": "ruby",
}


def detect_language(path: str) -> str:
    return EXT_LANG.get(os.path.splitext(path)[1], "unknown")


def walk_repo(root: str):
    """Yield source file paths under root, skipping noise directories."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for fname in filenames:
            path = os.path.join(dirpath, fname)
            if detect_language(path) != "unknown":
                yield path
