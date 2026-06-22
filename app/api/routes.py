import logging
from pathlib import Path
import numpy as np
import cv2
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import FileResponse

import config
from app.core.indexer import get_face_model, extract_embedding
from app.core.searcher import FaceSearcher

_STATIC_DIR = Path(__file__).parent.parent.parent / "static"

logger = logging.getLogger(__name__)

router = APIRouter()

searcher = FaceSearcher(config.INDEX_PATH, config.SEARCH_THRESHOLD, config.MAX_RESULTS)
face_model = get_face_model()


@router.get("/")
def index():
    return FileResponse(_STATIC_DIR / "index.html")


@router.post("/search")
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


@router.post("/reload-index")
def reload_index():
    searcher.reload(config.INDEX_PATH)
    return {"status": "ok", "indexed": int(len(searcher.image_ids))}


@router.get("/health")
def health():
    count = int(len(searcher.image_ids)) if searcher.image_ids is not None else 0
    return {"status": "ok", "indexed_faces": count}


@router.get("/photo")
def serve_photo(path: str):
    p = Path(path).resolve()
    try:
        p.relative_to(config.PHOTOS_DIR)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    if not p.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(p))
