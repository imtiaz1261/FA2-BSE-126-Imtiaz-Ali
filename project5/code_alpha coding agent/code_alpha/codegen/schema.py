from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EditOp(str, Enum):
    REPLACE = "replace"   # replace lines [start_line, end_line] (1-indexed, inclusive)
    INSERT = "insert"     # insert new_content before start_line, nothing removed
    CREATE = "create"     # create a brand-new file at file_path


@dataclass
class Edit:
    """One structured edit. Line ranges, not full-file rewrites, so diffs
    stay minimal and reviewable — matches Module 5's design goal directly."""
    op: EditOp
    file_path: str
    new_content: str
    start_line: Optional[int] = None          # required for replace/insert
    end_line: Optional[int] = None             # required for replace
    expected_old_content: Optional[str] = None  # conflict check: must match
                                                 # current lines[start:end] exactly,
                                                 # or the edit is rejected rather
                                                 # than silently overwriting
                                                 # something the LLM didn't see.

    def __post_init__(self):
        if self.op in (EditOp.REPLACE, EditOp.INSERT) and self.start_line is None:
            raise ValueError(f"{self.op} requires start_line")
        if self.op == EditOp.REPLACE and self.end_line is None:
            raise ValueError("replace requires end_line")
