"""Vercel Python serverless entry-point.

Since Vercel root is set to backend/, this file is at the root's api/index.py
from Vercel's perspective. sys.path is patched so 'from app.xxx import yyy'
resolves against the backend/ directory.
"""

import sys
import os

# __file__ = <deploy_root>/api/index.py
# parent   = <deploy_root>/          (which is the backend/ folder)
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Vercel picks up the 'app' name as the ASGI handler automatically
from app.main import app  # noqa: E402, F401
