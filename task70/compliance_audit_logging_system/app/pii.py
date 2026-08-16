import re
PATTERNS=[
(re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)"),"[REDACTED_CREDIT_CARD]"),
(re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),"[REDACTED_SSN]"),
(re.compile(r"\b[A-Z]{1,3}-?\d{6,12}\b",re.I),"[REDACTED_ID]"),
(re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),"[REDACTED_EMAIL]"),
(re.compile(r"(?<!\d)(?:\+?92|0)\s?3\d{2}[- ]?\d{7}(?!\d)"),"[REDACTED_PHONE]")]
def mask_pii(value):
    for p,r in PATTERNS: value=p.sub(r,value or "")
    return value
