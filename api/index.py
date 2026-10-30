"""Vercel Python serverless entry-point for the FastAPI application.

Vercel exposes this file as a serverless function at the root path ('/').
The vercel.json routes ALL requests here via the catch-all rule.

sys.path is patched so that 'from app.xxx import yyy' resolves
correctly against the backend/ directory.
"""

import sys
import os

# backend/ is a sibling of api/ at the repo root
# e.g. repo_root/api/index.py  ->  repo_root/backend/
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir = os.path.join(repo_root, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Re-export the FastAPI ASGI app — Vercel picks up the 'app' name automatically
from app.main import app  # noqa: E402, F401
