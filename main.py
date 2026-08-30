# main.py
"""
Root entrypoint for FastAPI Cloud and ASGI servers.
Forwards the FastAPI application instance from backend.main.
"""
import os
import sys

backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from backend.main import app
