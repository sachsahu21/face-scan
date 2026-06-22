import logging
import numpy as np
import cv2
from pathlib import Path
from typing import Optional

from .sources.base import PhotoSource

logger = logging.getLogger(__name__)


def get_face_model():
    try:
        from insightface.app import FaceAnalysis
        model = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
        model.prepare(ctx_id=0, det_size=(640, 640))
        return model
    except ImportError:
        raise ImportError(
            "Missing dependency. Run:\n  pip install insightface onnxruntime"
        )


def extract_embedding(model, img: np.ndarray) -> Optional[np.ndarray]:
    """Return 512-d normalized face embedding for the largest face, or None."""
    faces = model.get(img)
    if not faces:
        return None
    largest = max(
        faces,
        key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1])
    )
    return largest.normed_embedding  # already L2-normalized


def build_index(source: PhotoSource, index_path: str, force: bool = False) -> int:
    """
    Generate face embeddings for all images in source and save to disk.
    Incremental: skips images already in the index unless force=True.
    """
    path = Path(index_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    embeddings: list = []
    image_ids: list = []

    if path.exists() and not force:
        data = np.load(path, allow_pickle=True)
        embeddings = list(data['embeddings'])
        image_ids = list(data['image_ids'])
        logger.info(f"Existing index loaded: {len(image_ids)} faces")

    existing = set(image_ids)
    all_images = source.list_images()
    new_images = [i for i in all_images if i not in existing]

    logger.info(f"Total images: {len(all_images)} | New to index: {len(new_images)}")

    if not new_images:
        logger.info("Nothing new to index.")
        return len(image_ids)

    model = get_face_model()
    faces_found = 0

    for i, image_id in enumerate(new_images):
        try:
            img = source.read_image(image_id)
            emb = extract_embedding(model, img)
            if emb is not None:
                embeddings.append(emb)
                image_ids.append(image_id)
                faces_found += 1
            else:
                logger.debug(f"No face: {image_id}")
        except Exception as e:
            logger.warning(f"Skipping {image_id}: {e}")

        if (i + 1) % 50 == 0:
            logger.info(f"  {i + 1}/{len(new_images)} processed | {faces_found} faces found")

    if embeddings:
        np.savez(
            path,
            embeddings=np.array(embeddings, dtype=np.float32),
            image_ids=np.array(image_ids),
        )
        logger.info(f"Index saved → {path} ({len(image_ids)} total faces)")

    return len(image_ids)
