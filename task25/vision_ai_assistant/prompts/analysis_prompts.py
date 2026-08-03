"""
prompts/analysis_prompts.py
============================
Prompts used for document analysis tasks:
  - Initial image analysis (what is this document?)
  - OCR / full text extraction
  - Summary generation
  - Follow-up question answering
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Initial analysis — run immediately after image upload
# ---------------------------------------------------------------------------
INITIAL_ANALYSIS_PROMPT = """Analyze this document image and provide a comprehensive overview.

Please structure your response as follows:

## Document Overview
- **Type**: [what kind of document is this?]
- **Language**: [primary language]
- **Condition**: [clear / partially legible / damaged / low quality]

## Summary
[2-3 sentences describing what this document is and its key purpose]

## Key Information Found
[List the most important fields/values visible — amounts, dates, names, reference numbers]

## What I Can Help You With
[Suggest 3-4 specific questions the user might want to ask about this document]

Be specific and accurate. Only report what is clearly visible in the image.
"""

# ---------------------------------------------------------------------------
# Full OCR extraction
# ---------------------------------------------------------------------------
OCR_FULL_TEXT_PROMPT = """Perform a complete OCR (optical character recognition) on this image.

Extract ALL visible text exactly as it appears, preserving:
- Line breaks
- Table structure (use | to separate columns)
- Indentation where meaningful
- Special characters, symbols, and currency signs

Format your response as:
## Extracted Text
```
[all extracted text here]
```

## OCR Notes
[Any text that was unclear, partially visible, or uncertain — note these specifically]
"""

# ---------------------------------------------------------------------------
# Document summary prompt
# ---------------------------------------------------------------------------
SUMMARY_PROMPT = """Provide a concise professional summary of this document.

Include:
1. **Document Type and Purpose**: What is this document and what is it for?
2. **Key Parties**: Who are the main people/organizations involved?
3. **Critical Values**: The most important numbers, dates, or amounts
4. **Status/Action Required**: Is there anything that requires attention?

Keep the summary under 150 words. Be precise and professional.
"""

# ---------------------------------------------------------------------------
# Specific question answering (injected as user turn)
# ---------------------------------------------------------------------------
QUESTION_ANSWER_PREFIX = """Based on the document image provided, please answer the following question accurately and concisely:

"""

# ---------------------------------------------------------------------------
# Follow-up question context reminder
# ---------------------------------------------------------------------------
FOLLOWUP_CONTEXT_REMINDER = """[Note: This is a follow-up question about the same document. 
Use your memory of the previously extracted information to answer accurately.]

"""

# ---------------------------------------------------------------------------
# JSON re-extraction request (when user asks for JSON mid-conversation)
# ---------------------------------------------------------------------------
JSON_REQUEST_PROMPT = """Based on the document image and our conversation so far, 
extract all available information and return it as a structured JSON object.

Return valid JSON inside a ```json code block.
Use null for any fields not present in the document.
Include all information discussed in our conversation.
"""

# ---------------------------------------------------------------------------
# Table extraction prompt
# ---------------------------------------------------------------------------
TABLE_EXTRACTION_PROMPT = """Extract all tabular data from this document and present it as a formatted Markdown table.

For each table found:
1. Give it a heading describing what it contains
2. Present it as a proper Markdown table with header row
3. Preserve all values exactly as shown

If no table is present, describe the structured layout of the information instead.
"""

# ---------------------------------------------------------------------------
# Comparison / validation prompt
# ---------------------------------------------------------------------------
VALIDATION_PROMPT = """Review this document for the following:

1. **Completeness**: Are all required fields filled in?
2. **Consistency**: Do the numbers add up correctly? (e.g., line items sum = subtotal)
3. **Issues**: Note any missing information, inconsistencies, or potential errors
4. **Summary**: Provide an overall assessment

Be specific about any discrepancies found.
"""

# ---------------------------------------------------------------------------
# Multi-language analysis
# ---------------------------------------------------------------------------
def get_multilingual_prompt(detected_language: str) -> str:
    """Generate a language-aware analysis prompt."""
    return f"""This document appears to be in {detected_language}.

Please:
1. Extract all text in the original {detected_language}
2. Provide English translations for key fields in parentheses
3. Use the format: "Original text (English translation)"
4. Note any translation uncertainties

Then proceed with the standard document analysis.
"""

# ---------------------------------------------------------------------------
# Dynamic question prompt builder
# ---------------------------------------------------------------------------
def build_question_prompt(question: str, has_prior_context: bool = False) -> str:
    """
    Build the user-turn prompt for a Q&A request.

    Args:
        question: The user's natural language question
        has_prior_context: True if this is a follow-up in an existing conversation

    Returns:
        Formatted prompt string
    """
    prefix = FOLLOWUP_CONTEXT_REMINDER if has_prior_context else ""
    return f"{prefix}{question}"


# ---------------------------------------------------------------------------
# Auto-suggest prompts based on document type
# ---------------------------------------------------------------------------
DOCUMENT_TYPE_SUGGESTIONS: dict[str, list[str]] = {
    "invoice": [
        "What is the total amount due?",
        "Extract all line items as a table",
        "When is the payment due?",
        "Who is the vendor and customer?",
        "Extract all information as JSON",
    ],
    "receipt": [
        "What is the total amount paid?",
        "List all purchased items",
        "What payment method was used?",
        "What is the purchase date and time?",
        "Extract all information as JSON",
    ],
    "bank_statement": [
        "What is the closing balance?",
        "List all debit transactions",
        "What is the total amount debited this period?",
        "Are there any unusual transactions?",
        "Extract all transactions as JSON",
    ],
    "business_card": [
        "What is the person's full name and title?",
        "What is their email address?",
        "What company do they work for?",
        "Extract all contact details as JSON",
    ],
    "diagram": [
        "Explain this diagram step by step",
        "What are the main components?",
        "What process does this flowchart describe?",
        "What is the starting point and end point?",
        "Extract the diagram structure as JSON",
    ],
    "flowchart": [
        "Walk me through this flowchart",
        "What decision points are there?",
        "What is the main process being described?",
        "Extract the flowchart structure as JSON",
    ],
    "form": [
        "Which fields are filled in?",
        "Which required fields are empty?",
        "What is the purpose of this form?",
        "Extract all field values as JSON",
    ],
    "handwritten_note": [
        "Transcribe all the handwritten text",
        "What are the key points mentioned?",
        "Who wrote this and when?",
        "Summarize the content",
    ],
    "medical_report": [
        "What type of medical document is this?",
        "What are the key findings?",
        "What medications are mentioned?",
        "Summarize the document (demo only)",
    ],
    "id_card": [
        "What type of ID document is this?",
        "What country issued this document?",
        "When does it expire?",
        "Extract document details as JSON (demo only)",
    ],
    "unknown": [
        "What type of document is this?",
        "Extract all visible text",
        "Summarize this document",
        "Extract all information as JSON",
    ],
}


def get_suggestions_for_document(document_type: str) -> list[str]:
    """Return suggested follow-up questions for a detected document type."""
    return DOCUMENT_TYPE_SUGGESTIONS.get(
        document_type,
        DOCUMENT_TYPE_SUGGESTIONS["unknown"],
    )
