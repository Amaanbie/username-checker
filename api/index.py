from app import app

# Vercel's Python runtime looks for a WSGI/ASGI callable named `app` or `handler`.
handler = app
