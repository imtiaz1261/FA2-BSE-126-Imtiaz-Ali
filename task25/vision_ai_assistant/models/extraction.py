"""
models/extraction.py
====================
Per-document-type structured extraction schemas.

Each class maps exactly to what the LLM is asked to return in JSON.
Using Optional fields everywhere because real-world documents may be
partially legible or missing certain fields.

Classes:
    LineItem            — invoice / receipt row
    InvoiceExtraction   — full invoice schema
    ReceiptExtraction   — retail receipt
    BankStatementExtraction
    BusinessCardExtraction
    DiagramExtraction
    FormExtraction
    HandwrittenExtraction
    MedicalReportExtraction
    IDCardExtraction
    GenericExtraction   — fallback for unknown documents
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared sub-objects
# ---------------------------------------------------------------------------
class LineItem(BaseModel):
    """One row in an invoice or receipt."""
    description: Optional[str] = None
    quantity: Optional[str] = None
    unit_price: Optional[str] = None
    total: Optional[str] = None
    sku: Optional[str] = None


class BankTransaction(BaseModel):
    """One row in a bank statement."""
    date: Optional[str] = None
    description: Optional[str] = None
    debit: Optional[str] = None
    credit: Optional[str] = None
    balance: Optional[str] = None
    reference: Optional[str] = None


class Address(BaseModel):
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None

    def as_string(self) -> str:
        parts = [
            self.street, self.city, self.state,
            self.postal_code, self.country,
        ]
        return ", ".join(p for p in parts if p)


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------
class InvoiceExtraction(BaseModel):
    """Structured data extracted from an invoice document."""
    vendor_name: Optional[str] = None
    vendor_address: Optional[str] = None
    vendor_email: Optional[str] = None
    vendor_phone: Optional[str] = None
    vendor_website: Optional[str] = None
    customer_name: Optional[str] = None
    customer_address: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    purchase_order: Optional[str] = None
    currency: Optional[str] = None
    subtotal: Optional[str] = None
    discount: Optional[str] = None
    tax: Optional[str] = None
    tax_rate: Optional[str] = None
    shipping: Optional[str] = None
    total_amount: Optional[str] = None
    amount_paid: Optional[str] = None
    balance_due: Optional[str] = None
    payment_terms: Optional[str] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None
    line_items: List[LineItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Receipt
# ---------------------------------------------------------------------------
class ReceiptExtraction(BaseModel):
    """Structured data extracted from a retail receipt."""
    store_name: Optional[str] = None
    store_address: Optional[str] = None
    store_phone: Optional[str] = None
    cashier: Optional[str] = None
    register_number: Optional[str] = None
    transaction_id: Optional[str] = None
    purchase_date: Optional[str] = None
    purchase_time: Optional[str] = None
    currency: Optional[str] = None
    subtotal: Optional[str] = None
    discount: Optional[str] = None
    tax: Optional[str] = None
    tip: Optional[str] = None
    total: Optional[str] = None
    payment_method: Optional[str] = None
    items: List[LineItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Bank Statement
# ---------------------------------------------------------------------------
class BankStatementExtraction(BaseModel):
    """Structured data extracted from a bank statement."""
    bank_name: Optional[str] = None
    account_holder: Optional[str] = None
    account_number: Optional[str] = None
    account_type: Optional[str] = None
    iban: Optional[str] = None
    sort_code: Optional[str] = None
    statement_period_start: Optional[str] = None
    statement_period_end: Optional[str] = None
    opening_balance: Optional[str] = None
    closing_balance: Optional[str] = None
    total_credits: Optional[str] = None
    total_debits: Optional[str] = None
    currency: Optional[str] = None
    transactions: List[BankTransaction] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Business Card
# ---------------------------------------------------------------------------
class BusinessCardExtraction(BaseModel):
    """Structured data extracted from a business card."""
    full_name: Optional[str] = None
    job_title: Optional[str] = None
    company: Optional[str] = None
    department: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    fax: Optional[str] = None
    website: Optional[str] = None
    linkedin: Optional[str] = None
    twitter: Optional[str] = None
    address: Optional[str] = None


# ---------------------------------------------------------------------------
# Diagram / Flowchart
# ---------------------------------------------------------------------------
class DiagramComponent(BaseModel):
    id: Optional[str] = None
    label: Optional[str] = None
    type: Optional[str] = None        # "node", "decision", "process", …
    description: Optional[str] = None


class DiagramRelationship(BaseModel):
    from_id: Optional[str] = None
    to_id: Optional[str] = None
    label: Optional[str] = None


class DiagramExtraction(BaseModel):
    """Structured data extracted from a diagram or flowchart."""
    title: Optional[str] = None
    diagram_type: Optional[str] = None   # "flowchart", "UML", "ERD", …
    summary: Optional[str] = None
    components: List[DiagramComponent] = Field(default_factory=list)
    relationships: List[DiagramRelationship] = Field(default_factory=list)
    key_concepts: List[str] = Field(default_factory=list)
    start_node: Optional[str] = None
    end_node: Optional[str] = None


# ---------------------------------------------------------------------------
# Form
# ---------------------------------------------------------------------------
class FormField(BaseModel):
    label: Optional[str] = None
    value: Optional[str] = None
    field_type: Optional[str] = None    # "text", "checkbox", "signature", …
    is_filled: Optional[bool] = None


class FormExtraction(BaseModel):
    """Structured data extracted from a form."""
    form_title: Optional[str] = None
    form_number: Optional[str] = None
    issuing_authority: Optional[str] = None
    date: Optional[str] = None
    fields: List[FormField] = Field(default_factory=list)
    signatures: List[str] = Field(default_factory=list)
    checkboxes: Dict[str, bool] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Handwritten Note
# ---------------------------------------------------------------------------
class HandwrittenExtraction(BaseModel):
    """Transcription of a handwritten document."""
    transcribed_text: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None
    subject: Optional[str] = None
    key_points: List[str] = Field(default_factory=list)
    legibility_score: Optional[str] = None   # "high" / "medium" / "low"
    language: Optional[str] = None


# ---------------------------------------------------------------------------
# Medical Report (Demo — no real patient data)
# ---------------------------------------------------------------------------
class MedicalReportExtraction(BaseModel):
    """Demo-only extraction for medical documents."""
    document_type: Optional[str] = None
    patient_id: Optional[str] = None         # never real name
    date: Optional[str] = None
    facility: Optional[str] = None
    department: Optional[str] = None
    findings: Optional[str] = None
    diagnosis: Optional[str] = None
    medications: List[str] = Field(default_factory=list)
    test_results: Dict[str, str] = Field(default_factory=dict)
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# ID Card (Demo)
# ---------------------------------------------------------------------------
class IDCardExtraction(BaseModel):
    """Demo-only extraction for ID card documents."""
    document_type: Optional[str] = None      # "Passport", "Driver's License", …
    country: Optional[str] = None
    id_number: Optional[str] = None          # redacted in UI
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    expiry_date: Optional[str] = None
    nationality: Optional[str] = None
    issuing_authority: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Generic fallback
# ---------------------------------------------------------------------------
class GenericExtraction(BaseModel):
    """Fallback when document type cannot be determined."""
    document_title: Optional[str] = None
    detected_type: Optional[str] = None
    all_text: Optional[str] = None
    key_value_pairs: Dict[str, str] = Field(default_factory=dict)
    dates_found: List[str] = Field(default_factory=list)
    amounts_found: List[str] = Field(default_factory=list)
    names_found: List[str] = Field(default_factory=list)
    summary: Optional[str] = None


# ---------------------------------------------------------------------------
# Union type for type-checking
# ---------------------------------------------------------------------------
AnyExtraction = (
    InvoiceExtraction
    | ReceiptExtraction
    | BankStatementExtraction
    | BusinessCardExtraction
    | DiagramExtraction
    | FormExtraction
    | HandwrittenExtraction
    | MedicalReportExtraction
    | IDCardExtraction
    | GenericExtraction
)

# Mapping from DocumentType string → extraction class
EXTRACTION_SCHEMA_MAP: Dict[str, type] = {
    "invoice":          InvoiceExtraction,
    "receipt":          ReceiptExtraction,
    "bank_statement":   BankStatementExtraction,
    "business_card":    BusinessCardExtraction,
    "diagram":          DiagramExtraction,
    "flowchart":        DiagramExtraction,
    "form":             FormExtraction,
    "handwritten_note": HandwrittenExtraction,
    "medical_report":   MedicalReportExtraction,
    "id_card":          IDCardExtraction,
    "unknown":          GenericExtraction,
}


def get_extraction_schema(document_type: str) -> type:
    """Return the Pydantic model class for a given document type string."""
    return EXTRACTION_SCHEMA_MAP.get(document_type, GenericExtraction)


def get_empty_extraction(document_type: str) -> BaseModel:
    """Return an empty (all-None) instance of the correct schema."""
    cls = get_extraction_schema(document_type)
    return cls()
