from __future__ import annotations
import random
import uuid
from dataclasses import dataclass
from typing import Optional
from .prompts import PROMPTS

@dataclass
class Assignment:
    interaction_id: str
    variant: str
    system_prompt: str

def assign_variant(variant_a_weight: float = 0.5,
                   rng: Optional[random.Random] = None) -> Assignment:
    if not 0 < variant_a_weight < 1:
        raise ValueError("variant_a_weight must be between 0 and 1")
    rng = rng or random
    variant = "A" if rng.random() < variant_a_weight else "B"
    return Assignment(str(uuid.uuid4()), variant, PROMPTS[variant])

def response_length(text: str) -> int:
    return len(text.split())

def validate_feedback(feedback: Optional[str]) -> Optional[str]:
    if feedback is None:
        return None
    if feedback not in {"up", "down"}:
        raise ValueError("feedback must be 'up', 'down', or None")
    return feedback
