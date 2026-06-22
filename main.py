"""
FastAPI server — face search API.

Run:
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""
import logging
import numpy as np
import cv2
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import config
from app.indexer import get_face_model, extract_embedding
from app.searcher import FaceSearcher

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Face Scan")

searcher = FaceSearcher(config.INDEX_PATH, config.SEARCH_THRESHOLD, config.MAX_RESULTS)
face_model = get_face_model()

app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(f"{config.STATIC_DIR}/index.html")


@app.post("/search")
async def search(file: UploadFile = File(...)):
    data = await file.read()
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Could not decode image")

    emb = extract_embedding(face_model, img)
    if emb is None:
        raise HTTPException(status_code=422, detail="No face detected in the uploaded image")

    results = searcher.search(emb)
    return {"results": results, "total": len(results)}


@app.post("/reload-index")
def reload_index():
    searcher.reload(config.INDEX_PATH)
    return {"status": "ok", "indexed": len(searcher.image_ids)}


@app.get("/health")
def health():
    return {"status": "ok", "indexed_faces": len(searcher.image_ids) if searcher.image_ids is not None else 0}
