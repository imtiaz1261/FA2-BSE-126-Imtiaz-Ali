"""Quick smoke test for the services module (no API key required)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import warnings
warnings.filterwarnings("error", category=DeprecationWarning)

from PIL import Image
from io import BytesIO

# ── vision_service ──────────────────────────────────────────────────────────
from services.vision_service import process_uploaded_file, resize_image_for_display

img = Image.new("RGB", (200, 150), color=(73, 109, 137))
buf = BytesIO()
img.save(buf, format="JPEG")
fake_jpg = buf.getvalue()

uploaded, err = process_uploaded_file(fake_jpg, "test_invoice.jpg")
assert err is None, f"Expected no error, got: {err}"
assert uploaded.metadata.width == 200
assert uploaded.metadata.format == "JPEG"
assert uploaded.data_uri.startswith("data:image/jpeg;base64,")
assert len(uploaded.sha256) == 64
print(f"  process_uploaded_file      : OK | {uploaded.metadata.dimensions_str}")

_, err2 = process_uploaded_file(b"x" * (21 * 1024 * 1024), "huge.jpg")
assert err2 and "large" in err2.lower()
print(f"  size limit check           : OK")

_, err3 = process_uploaded_file(fake_jpg, "doc.bmp")
assert err3 and "Unsupported" in err3
print(f"  unsupported format check   : OK")

small = resize_image_for_display(fake_jpg, max_width=100, max_height=100)
assert len(small) > 0
print(f"  resize_image_for_display   : OK")

# ── json_extractor ───────────────────────────────────────────────────────────
from services.json_extractor import (
    extract_json_from_text, parse_llm_json,
    process_extraction_response, format_json_for_display,
    extraction_to_markdown_table, _clean_dict,
)

# Plain JSON
assert extract_json_from_text('{"a": "b"}') == '{"a": "b"}'
print(f"  extract_json (plain)       : OK")

# Fenced JSON
fenced = '```json\n{"invoice_number": "INV-001"}\n```'
result = extract_json_from_text(fenced)
assert result is not None and "INV-001" in result
print(f"  extract_json (fenced)      : OK")

# Prose wrapper
prose = 'Here is the data:\n{"vendor": "ACME"}\nEnd.'
result2 = extract_json_from_text(prose)
assert result2 and "ACME" in result2
print(f"  extract_json (prose)       : OK")

# Full extraction pipeline
llm_out = '{"vendor_name": "ACME Corp", "invoice_number": "INV-042", "total_amount": "2450.75", "currency": "GBP", "line_items": []}'
instance, data, err = process_extraction_response(llm_out, "invoice")
assert instance is not None, f"Expected instance, got None. err={err}"
assert data["vendor_name"] == "ACME Corp"
print(f"  process_extraction_response: OK | vendor={data['vendor_name']}")

# Trailing comma repair
trailing = '{"name": "John", "age": 30,}'
from services.json_extractor import _attempt_json_repair, _is_valid_json
repaired = _attempt_json_repair(trailing)
assert _is_valid_json(repaired), "Trailing comma repair failed"
print(f"  trailing comma repair      : OK")

# Clean dict
dirty = {"name": "John", "email": "N/A", "phone": "", "company": None}
clean = _clean_dict(dirty)
assert clean["email"] is None
assert clean["phone"] is None
print(f"  _clean_dict                : OK")

# Format / table
pretty = format_json_for_display({"vendor": "ACME", "total": "500"})
assert "ACME" in pretty
table = extraction_to_markdown_table({"vendor_name": "ACME", "total": "500"}, "Invoice")
assert "| Vendor Name |" in table
print(f"  format_json_for_display    : OK")
print(f"  extraction_to_markdown_table: OK")

# ── package imports ──────────────────────────────────────────────────────────
from services import (
    VisionService, process_uploaded_file,
    LLMService, create_llm_service, validate_api_key,
    process_extraction_response, format_json_for_display,
)
print(f"  services package imports   : OK")

print()
print("All services tests: PASS")
