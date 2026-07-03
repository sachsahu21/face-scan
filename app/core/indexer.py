import logging
import numpy as np
import cv2
from pathlib import Path
from typing import Optional

from app.sources.base import PhotoSource

logger = logging.getLogger(__name__)

# Module-level singleton so the model is never loaded twice in the same process.
_face_model = None

CHECKPOINT_EVERY = 500  # save a partial index after this many new images


def get_face_model():
    global _face_model
    if _face_model is not None:
        return _face_model
    try:
        from insightface.app import FaceAnalysis
        _face_model = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
        _face_model.prepare(ctx_id=0, det_size=(640, 640))
        return _face_model
    except ImportError:
        raise ImportError("Run:  pip install insightface onnxruntime")


def extract_embedding(model, img: np.ndarray) -> Optional[np.ndarray]:
    """Return 512-d normalized face embedding for the largest face, or None."""
    faces = model.get(img)
    if not faces:
        return None
    largest = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    return largest.normed_embedding  # already L2-normalized


def _save_index(index_path: Path, embeddings: list, image_ids: list):
    np.savez(
        index_path,
        embeddings=np.array(embeddings, dtype=np.float32),
        image_ids=np.array(image_ids),
    )


def build_index(source: PhotoSource, index_path: Path, force: bool = False) -> int:
    """
    Build or incrementally update the face embeddings index.
    Skips images already in the index unless force=True.
    Checkpoints to disk every CHECKPOINT_EVERY images so progress is not
    lost if the process is killed mid-way.
    Returns total number of indexed faces.
    """
    index_path = Path(index_path)
    index_path.parent.mkdir(parents=True, exist_ok=True)

    embeddings: list = []
    image_ids: list = []

    if index_path.exists() and not force:
        data = np.load(index_path, allow_pickle=True)
        embeddings = list(data['embeddings'])
        image_ids = list(data['image_ids'])
        logger.info(f"Loaded existing index: {len(image_ids)} faces")

    existing = set(image_ids)
    all_images = source.list_images()
    new_images = [i for i in all_images if i not in existing]

    logger.info(f"Total images: {len(all_images)} | New to index: {len(new_images)}")

    if not new_images:
        logger.info("Nothing new to index.")
        return len(image_ids)

    model = get_face_model()
    faces_found = 0
    since_checkpoint = 0

    for i, image_id in enumerate(new_images):
        try:
            img = source.read_image(image_id)
            emb = extract_embedding(model, img)
            if emb is not None:
                embeddings.append(emb)
                image_ids.append(image_id)
                faces_found += 1
                since_checkpoint += 1
            else:
                logger.debug(f"No face: {image_id}")
        except Exception as e:
            logger.warning(f"Skipping {image_id}: {e}")

        if (i + 1) % 50 == 0:
            logger.info(f"  {i + 1}/{len(new_images)} processed | {faces_found} faces found")

        # Checkpoint so a killed process doesn't lose all progress.
        if since_checkpoint >= CHECKPOINT_EVERY and embeddings:
            _save_index(index_path, embeddings, image_ids)
            logger.info(f"  Checkpoint saved ({len(image_ids)} total faces)")
            since_checkpoint = 0

    if embeddings:
        _save_index(index_path, embeddings, image_ids)
        logger.info(f"Index saved → {index_path} ({len(image_ids)} total faces)")

    return len(image_ids)
