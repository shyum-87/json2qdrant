r"""Compatibility wrapper for the Streamlit diagnostic helper.

This wrapper lives at the repository root so users can run:

    python .\diagnose_streamlit_env.py

It delegates to scripts/diagnose_streamlit_env.py.
"""

from __future__ import annotations

import runpy
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "scripts" / "diagnose_streamlit_env.py"

if __name__ == "__main__":
    runpy.run_path(str(SCRIPT), run_name="__main__")
