"""
Vercel entry point — re-exports the FastAPI app from app/main.py.
Vercel's Python runtime looks for a WSGI/ASGI `app` object in this file.
"""
import sys
import os

# Ensure the project root is on sys.path so `from app import ...` works
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.main import app  # noqa: F401  — Vercel picks this up automatically
