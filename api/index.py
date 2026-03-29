"""
Vercel serverless entry point — wraps the FastAPI app with Mangum (ASGI → Lambda adapter).
All routes (/optimize, /radio/*, /airports, etc.) are forwarded here via vercel.json rewrites.
"""
import sys
import os

# Add backend directory to path so relative imports in main.py work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from main import app  # FastAPI app instance
from mangum import Mangum

# Mangum converts ASGI (FastAPI) to a format Vercel's Python runtime understands
handler = Mangum(app, lifespan="off")
