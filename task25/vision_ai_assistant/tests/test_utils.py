"""Smoke tests for the utils module — no API key, no Streamlit required."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image
from io import BytesIO
from datetime import datetime, timezone, timedelta

# ── image_utils ─────────────────────────────────────────────────────────────
from utils.image_utils import (
    make_thumbnail, make_display_image,
    bytes_to_base64_img_tag, image_to_base64_str,
    get_image_info, is_valid_image_bytes, get_image_mime_type,
)

def make_fake_image(w=400, h=300, fmt="JPEG") -> bytes:
    img = Image.new("RGB", (w, h), color=(100, 150, 200))
    buf = BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()

raw = make_fake_image(800, 600)

thumb = make_thumbnail(raw, size=(200, 150))
assert len(thumb) > 0
img_check = Image.open(BytesIO(thumb))
assert img_check.width <= 200 and img_check.height <= 150
print("  make_thumbnail             : OK")

display = make_display_image(raw, max_width=400, max_height=300)
assert len(display) > 0
print("  make_display_image         : OK")

tag = bytes_to_base64_img_tag(raw, alt="Test")
assert tag.startswith("<img") and "base64" in tag
print("  bytes_to_base64_img_tag    : OK")

b64 = image_to_base64_str(raw)
assert len(b64) > 100
print("  image_to_base64_str        : OK")

info = get_image_info(raw, "test.jpg")
assert info["Dimensions"] == "800 × 600 px"
assert info["Format"] == "JPEG"
print("  get_image_info             : OK")

assert is_valid_image_bytes(raw) == True
assert is_valid_image_bytes(b"not an image") == False
print("  is_valid_image_bytes       : OK")

assert get_image_mime_type("file.jpg")  == "image/jpeg"
assert get_image_mime_type("file.png")  == "image/png"
assert get_image_mime_type("file.webp") == "image/webp"
print("  get_image_mime_type        : OK")

# ── helpers ──────────────────────────────────────────────────────────────────
from utils.helpers import (
    truncate, contains_json, contains_markdown_table,
    extract_code_blocks, strip_markdown, estimate_tokens,
    now_utc, format_timestamp, time_ago,
    document_type_badge, confidence_badge, SSKey,
)

assert truncate("Hello World", 8) == "Hello W…"
assert truncate("Hi", 10)         == "Hi"
print("  truncate                   : OK")

assert contains_json('{"key": "val"}')     == True
assert contains_json("no json here")       == False
print("  contains_json              : OK")

assert contains_markdown_table("| A | B |\n|---|---|") == True
print("  contains_markdown_table   : OK")

blocks = extract_code_blocks("```json\n{\"a\":1}\n```")
assert len(blocks) == 1 and blocks[0]["language"] == "json"
print("  extract_code_blocks        : OK")

plain = strip_markdown("# Title\n**bold** and `code`")
assert "#" not in plain and "**" not in plain
print("  strip_markdown             : OK")

assert estimate_tokens("Hello world") > 0
print("  estimate_tokens            : OK")

now = now_utc()
assert now.tzinfo is not None
ts  = format_timestamp(now)
assert ":" in ts
print("  now_utc / format_timestamp : OK")

past = now - timedelta(minutes=5)
ago  = time_ago(past)
assert "min" in ago
print("  time_ago                   : OK")

badge = document_type_badge("invoice")
assert "Invoice" in badge
print("  document_type_badge        : OK")

cb = confidence_badge(0.92)
assert "92%" in cb
print("  confidence_badge           : OK")

# ── export_utils ─────────────────────────────────────────────────────────────
from utils.export_utils import export_json, export_markdown, export_txt, export_pdf, export_docx
from models.document import ExtractionResult, DocumentAnalysis, UploadedImage
from services.vision_service import process_uploaded_file

# Build a minimal ExtractionResult
raw_img = make_fake_image()
uploaded, _ = process_uploaded_file(raw_img, "test_invoice.jpg")
analysis = DocumentAnalysis(
    image_sha256=uploaded.sha256,
    image_filename="test_invoice.jpg",
    document_type="invoice",
    document_type_confidence=0.95,
    initial_summary="This is a test invoice from ACME Corp.",
    language_detected="English",
    model_used="gpt-4o",
    tokens_used=200,
)
result = ExtractionResult(
    session_id="test-session-1",
    image=uploaded,
    analysis=analysis,
    raw_extraction={"vendor_name": "ACME Corp", "total_amount": "500.00", "currency": "USD"},
)

# JSON
json_bytes, fname, mime = export_json(result)
assert b"ACME Corp" in json_bytes and mime == "application/json"
print(f"  export_json                : OK ({len(json_bytes)} bytes)")

# Markdown
md_bytes, fname, mime = export_markdown(result)
assert b"Invoice" in md_bytes or b"invoice" in md_bytes
print(f"  export_markdown            : OK ({len(md_bytes)} bytes)")

# TXT
txt_bytes, fname, mime = export_txt(result)
assert b"ACME" in txt_bytes
print(f"  export_txt                 : OK ({len(txt_bytes)} bytes)")

# PDF
pdf_bytes, fname, mime = export_pdf(result)
assert len(pdf_bytes) > 100
print(f"  export_pdf                 : OK ({len(pdf_bytes)} bytes, mime={mime})")

# DOCX
docx_bytes, fname, mime = export_docx(result)
assert len(docx_bytes) > 100
print(f"  export_docx                : OK ({len(docx_bytes)} bytes)")

# ── css_styles ───────────────────────────────────────────────────────────────
from utils.css_styles import get_main_css, get_loading_css

css = get_main_css()
assert "<style>" in css and "6366f1" in css
print("  get_main_css               : OK")

lcss = get_loading_css()
assert "<style>" in lcss
print("  get_loading_css            : OK")

# ── package imports ───────────────────────────────────────────────────────────
from utils import (
    make_thumbnail, export, get_main_css,
    SSKey, document_type_badge, time_ago,
)
print("  utils package imports      : OK")

print()
print("All utils tests: PASS")
