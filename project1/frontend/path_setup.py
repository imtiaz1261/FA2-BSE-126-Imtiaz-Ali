"""
frontend/path_setup.py
======================
Ensures the project root (the directory that *contains* the `frontend/`
package) is on sys.path so that ``from frontend.xxx import ...`` works no
matter which file Streamlit imports first, and regardless of the current
working directory.

Usage — add **one** line at the very top of every file that uses
absolute ``frontend.*`` imports, before those imports:

    import frontend.path_setup  # noqa: F401  (side-effect import)

This file is safe to import multiple times; the sys.path insertion is
guarded by a membership check.
"""
import sys
from pathlib import Path

# __file__ == .../project1/frontend/path_setup.py
# .parent   == .../project1/frontend/
# .parent.parent == .../project1/   <-- the project root we need
_project_root = str(Path(__file__).resolve().parent.parent)

if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
