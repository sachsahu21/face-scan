import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class FaceSearcher:
    def __init__(self, index_path: str, threshold: float = 0.35, max_results: int = 20):
        self.threshold = threshold
        self.max_results = max_results
        self.embeddings: Optional[np.ndarray] = None
        self.image_ids: Optional[np.ndarray] = None
        self._load(index_path)

    def _load(self, index_path: str):
        path = Path(index_path)
        if not path.exists():
            raise FileNotFoundError(
                f"No index found at {index_path}\n"
                "Run:  python scripts/build_index.py"
            )
        data = np.load(path, allow_pickle=True)
        self.embeddings = data['embeddings'].astype(np.float32)  # (N, 512)
        self.image_ids = data['image_ids']
        logger.info(f"Searcher ready: {len(self.image_ids)} indexed faces")

    def reload(self, index_path: str):
        self._load(index_path)

    def search(self, query_embedding: np.ndarray) -> List[Dict]:
        """
        Find images containing a face matching query_embedding.
        Returns list of {image_id, score} sorted by score descending.
        Scores are cosine similarities (0–1); embeddings are pre-normalized.
        """
        if self.embeddings is None or len(self.embeddings) == 0:
            return []

        scores = self.embeddings @ query_embedding  # cosine sim, shape (N,)
        matched = np.where(scores >= self.threshold)[0]

        if len(matched) == 0:
            return []

        top = matched[np.argsort(scores[matched])[::-1]][: self.max_results]
        return [
            {"image_id": str(self.image_ids[i]), "score": float(scores[i])}
            for i in top
        ]
