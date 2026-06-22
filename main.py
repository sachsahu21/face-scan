"""
Face Scan — entry point.

Run:
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import config
from app.api.routes import router

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

app = FastAPI(title="Face Scan")
app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")
app.include_router(router)
