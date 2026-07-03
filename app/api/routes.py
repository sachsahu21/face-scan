import logging
import threading
import time
from pathlib import Path
import numpy as np
import cv2
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

import config
from app.core.indexer import get_face_model, extract_embedding
from app.core.searcher import FaceSearcher

_STATIC_DIR = Path(__file__).parent.parent.parent / "static"

logger = logging.getLogger(__name__)

router = APIRouter()

# Index is small and fast to load — keep eager load at startup.
searcher = FaceSearcher(config.INDEX_PATH, config.SEARCH_THRESHOLD, config.MAX_RESULTS)

# Model is ~300 MB; load lazily on first request so the server becomes healthy
# immediately and the first real search pays the init cost.
_face_model = None
_model_lock = threading.Lock()


def _get_model():
    global _face_model
    if _face_model is None:
        with _model_lock:
            if _face_model is None:
                logger.info("Loading face model (first request)…")
                t0 = time.perf_counter()
                _face_model = get_face_model()
                logger.info(f"Face model ready in {time.perf_counter() - t0:.1f}s")
    return _face_model


@router.get("/")
def index():
    return FileResponse(_STATIC_DIR / "index.html")


@router.post("/warmup")
def warmup():
    """Pre-load the face model so the first real search is not slow."""
    _get_model()
    return {"status": "ok"}


@router.post("/search")
async def search(file: UploadFile = File(...)):
    t_start = time.perf_counter()

    data = await file.read()
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Could not decode image")

    t_decode = time.perf_counter()
    emb = extract_embedding(_get_model(), img)
    t_embed = time.perf_counter()

    if emb is None:
        raise HTTPException(status_code=422, detail="No face detected in the uploaded image")

    raw_results = searcher.search(emb)
    t_search = time.perf_counter()

    # For local source, drop results whose file no longer exists on disk.
    # For OneDrive, image_ids are OneDrive item IDs (not local paths) — keep all.
    if config.SOURCE_TYPE == "onedrive":
        results = raw_results
    else:
        results = [r for r in raw_results if Path(r["image_id"]).exists()]

    logger.debug(
        f"search: decode={t_decode - t_start:.3f}s "
        f"embed={t_embed - t_decode:.3f}s "
        f"search={t_search - t_embed:.3f}s "
        f"total={time.perf_counter() - t_start:.3f}s "
        f"hits={len(results)}"
    )

    return {"results": results, "total": len(results)}


@router.post("/reload-index")
def reload_index():
    searcher.reload(config.INDEX_PATH)
    return {"status": "ok", "indexed": int(len(searcher.image_ids))}


@router.get("/health")
def health():
    count = int(len(searcher.image_ids)) if searcher.image_ids is not None else 0
    return {"status": "ok", "indexed_faces": count, "model_loaded": _face_model is not None}


@router.get("/photo")
def serve_photo(path: str):
    """
    Local mode  → serve file bytes directly from disk.
    OneDrive mode → redirect browser to OneDrive thumbnail CDN URL (no proxying).
    """
    if config.SOURCE_TYPE == "onedrive":
        from app.sources.onedrive import OneDrivePhotoSource
        src = OneDrivePhotoSource(
            client_id=config.ONEDRIVE_CLIENT_ID,
            tenant_id=config.ONEDRIVE_TENANT_ID,
            folder=config.ONEDRIVE_FOLDER,
            token_cache_path=config.TOKEN_CACHE_PATH,
        )
        url = src.get_display_url(path)
        if not url:
            raise HTTPException(status_code=404, detail="Photo not available")
        return RedirectResponse(url=url)

    # Local mode
    p = Path(path).resolve()
    try:
        p.relative_to(config.PHOTOS_DIR)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    if not p.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(p))
