from pathlib import Path
BASE_DIR=Path(__file__).resolve().parent.parent
DATA_DIR=BASE_DIR/"data"; ARCHIVE_DIR=BASE_DIR/"archive"; DB_PATH=DATA_DIR/"audit.db"
RETENTION_DAYS=90
DATA_DIR.mkdir(exist_ok=True); ARCHIVE_DIR.mkdir(exist_ok=True)
