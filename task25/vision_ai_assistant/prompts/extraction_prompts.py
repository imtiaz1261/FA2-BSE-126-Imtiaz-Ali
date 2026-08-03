"""
prompts/extraction_prompts.py
==============================
Per-document-type extraction prompts.

Each prompt instructs the LLM to return a specific JSON schema.
The schema mirrors the Pydantic models in models/extraction.py.
"""

from __future__ import annotations

from typing import Dict


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------
INVOICE_EXTRACTION_PROMPT = """Extract ALL information from this invoice image and return a JSON object with this exact schema:

```json
{
  "vendor_name": null,
  "vendor_address": null,
  "vendor_email": null,
  "vendor_phone": null,
  "vendor_website": null,
  "customer_name": null,
  "customer_address": null,
  "invoice_number": null,
  "invoice_date": null,
  "due_date": null,
  "purchase_order": null,
  "currency": null,
  "subtotal": null,
  "discount": null,
  "tax": null,
  "tax_rate": null,
  "shipping": null,
  "total_amount": null,
  "amount_paid": null,
  "balance_due": null,
  "payment_terms": null,
  "payment_method": null,
  "notes": null,
  "line_items": [
    {
      "description": null,
      "quantity": null,
      "unit_price": null,
      "total": null,
      "sku": null
    }
  ]
}
```

Rules:
- Extract every line item visible on the invoice.
- Use null for any field not visible or not present.
- Preserve currency symbols and number formatting exactly as shown.
- Dates should be extracted as they appear (do not reformat).
"""

# ---------------------------------------------------------------------------
# Receipt
# ---------------------------------------------------------------------------
RECEIPT_EXTRACTION_PROMPT = """Extract ALL information from this receipt image and return a JSON object with this exact schema:

```json
{
  "store_name": null,
  "store_address": null,
  "store_phone": null,
  "cashier": null,
  "register_number": null,
  "transaction_id": null,
  "purchase_date": null,
  "purchase_time": null,
  "currency": null,
  "subtotal": null,
  "discount": null,
  "tax": null,
  "tip": null,
  "total": null,
  "payment_method": null,
  "items": [
    {
      "description": null,
      "quantity": null,
      "unit_price": null,
      "total": null,
      "sku": null
    }
  ]
}
```

Extract every purchased item visible on the receipt.
"""

# ---------------------------------------------------------------------------
# Bank Statement
# ---------------------------------------------------------------------------
BANK_STATEMENT_EXTRACTION_PROMPT = """Extract ALL information from this bank statement image and return a JSON object with this exact schema:

```json
{
  "bank_name": null,
  "account_holder": null,
  "account_number": null,
  "account_type": null,
  "iban": null,
  "sort_code": null,
  "statement_period_start": null,
  "statement_period_end": null,
  "opening_balance": null,
  "closing_balance": null,
  "total_credits": null,
  "total_debits": null,
  "currency": null,
  "transactions": [
    {
      "date": null,
      "description": null,
      "debit": null,
      "credit": null,
      "balance": null,
      "reference": null
    }
  ]
}
```

Extract every transaction row visible. If account number is partially masked (e.g. ****1234), extract it as shown.
"""

# ---------------------------------------------------------------------------
# Business Card
# ---------------------------------------------------------------------------
BUSINESS_CARD_EXTRACTION_PROMPT = """Extract ALL contact information from this business card image and return a JSON object with this exact schema:

```json
{
  "full_name": null,
  "job_title": null,
  "company": null,
  "department": null,
  "email": null,
  "phone": null,
  "mobile": null,
  "fax": null,
  "website": null,
  "linkedin": null,
  "twitter": null,
  "address": null
}
```

Extract all visible text from the card. If multiple phone numbers exist, use 'phone' for the primary office number and 'mobile' for the mobile/cell number.
"""

# ---------------------------------------------------------------------------
# Diagram / Flowchart
# ---------------------------------------------------------------------------
DIAGRAM_EXTRACTION_PROMPT = """Analyze this diagram/flowchart image and return a JSON object with this exact schema:

```json
{
  "title": null,
  "diagram_type": null,
  "summary": null,
  "components": [
    {
      "id": null,
      "label": null,
      "type": null,
      "description": null
    }
  ],
  "relationships": [
    {
      "from_id": null,
      "to_id": null,
      "label": null
    }
  ],
  "key_concepts": [],
  "start_node": null,
  "end_node": null
}
```

For diagram_type use: "flowchart", "UML class diagram", "UML sequence diagram", "ER diagram", "mind map", "org chart", "network diagram", "architecture diagram", or describe it specifically.
Assign simple IDs (A, B, C or 1, 2, 3) to components to define relationships.
"""

# ---------------------------------------------------------------------------
# Form
# ---------------------------------------------------------------------------
FORM_EXTRACTION_PROMPT = """Extract ALL information from this form image and return a JSON object with this exact schema:

```json
{
  "form_title": null,
  "form_number": null,
  "issuing_authority": null,
  "date": null,
  "fields": [
    {
      "label": null,
      "value": null,
      "field_type": null,
      "is_filled": null
    }
  ],
  "signatures": [],
  "checkboxes": {}
}
```

For field_type use: "text", "date", "number", "checkbox", "signature", "dropdown".
For is_filled: true if the field has a value, false if blank.
For checkboxes object, use the checkbox label as key and true/false as value.
"""

# ---------------------------------------------------------------------------
# Handwritten Note
# ---------------------------------------------------------------------------
HANDWRITTEN_EXTRACTION_PROMPT = """Transcribe and extract information from this handwritten document and return a JSON object with this exact schema:

```json
{
  "transcribed_text": null,
  "author": null,
  "date": null,
  "subject": null,
  "key_points": [],
  "legibility_score": null,
  "language": null
}
```

For legibility_score use: "high" (clearly legible), "medium" (mostly legible with some uncertainty), or "low" (difficult to read).
For transcribed_text, preserve line breaks using \\n.
For key_points, list the main ideas or action items mentioned.
If any word is illegible, use [illegible] in the transcription.
"""

# ---------------------------------------------------------------------------
# Medical Report (Demo)
# ---------------------------------------------------------------------------
MEDICAL_REPORT_EXTRACTION_PROMPT = """Extract information from this medical document (DEMO MODE — for demonstration purposes only) and return a JSON object with this exact schema:

```json
{
  "document_type": null,
  "patient_id": null,
  "date": null,
  "facility": null,
  "department": null,
  "findings": null,
  "diagnosis": null,
  "medications": [],
  "test_results": {},
  "notes": null
}
```

Important: This is a demo extraction. Do not extract or store real patient personal data. Use patient_id only if it is a non-identifying reference number.
"""

# ---------------------------------------------------------------------------
# ID Card (Demo)
# ---------------------------------------------------------------------------
ID_CARD_EXTRACTION_PROMPT = """Extract information from this ID document (DEMO MODE) and return a JSON object with this exact schema:

```json
{
  "document_type": null,
  "country": null,
  "id_number": null,
  "full_name": null,
  "date_of_birth": null,
  "expiry_date": null,
  "nationality": null,
  "issuing_authority": null,
  "notes": null
}
```

Note: This is a demo extraction only. In production, ID card processing must comply with GDPR and relevant data protection regulations.
"""

# ---------------------------------------------------------------------------
# Generic fallback
# ---------------------------------------------------------------------------
GENERIC_EXTRACTION_PROMPT = """Extract ALL visible information from this document image and return a JSON object with this exact schema:

```json
{
  "document_title": null,
  "detected_type": null,
  "all_text": null,
  "key_value_pairs": {},
  "dates_found": [],
  "amounts_found": [],
  "names_found": [],
  "summary": null
}
```

For key_value_pairs, extract any label: value patterns you see (e.g., "Reference: ABC123").
For amounts_found, include any monetary values with their currency symbols.
"""

# ---------------------------------------------------------------------------
# Prompt map keyed by document type
# ---------------------------------------------------------------------------
EXTRACTION_PROMPT_MAP: Dict[str, str] = {
    "invoice":          INVOICE_EXTRACTION_PROMPT,
    "receipt":          RECEIPT_EXTRACTION_PROMPT,
    "bank_statement":   BANK_STATEMENT_EXTRACTION_PROMPT,
    "business_card":    BUSINESS_CARD_EXTRACTION_PROMPT,
    "diagram":          DIAGRAM_EXTRACTION_PROMPT,
    "flowchart":        DIAGRAM_EXTRACTION_PROMPT,
    "form":             FORM_EXTRACTION_PROMPT,
    "handwritten_note": HANDWRITTEN_EXTRACTION_PROMPT,
    "medical_report":   MEDICAL_REPORT_EXTRACTION_PROMPT,
    "id_card":          ID_CARD_EXTRACTION_PROMPT,
    "unknown":          GENERIC_EXTRACTION_PROMPT,
}


def get_extraction_prompt(document_type: str) -> str:
    """Return the extraction prompt for a given document type."""
    return EXTRACTION_PROMPT_MAP.get(document_type, GENERIC_EXTRACTION_PROMPT)
