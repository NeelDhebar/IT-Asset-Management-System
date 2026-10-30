"""Vercel serverless entry-point.

Vercel's Python runtime requires the ASGI app to be importable from this file.
We add the backend directory to sys.path so all relative imports in app/ resolve correctly.
"""

import sys
import os

# Make the backend/ directory the importable root (so `from app.xxx import yyy` works)
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Import and re-export the FastAPI application
from app.main import app  # noqa: F401, E402
