import os
import cv2
import numpy as np
from pathlib import Path
from typing import List

from .base import PhotoSource

SUPPORTED = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}


class LocalPhotoSource(PhotoSource):
    def __init__(self, photos_dir: str):
        self.photos_dir = Path(photos_dir).resolve()
        if not self.photos_dir.exists():
            raise FileNotFoundError(f"Photos directory not found: {self.photos_dir}")

    def list_images(self) -> List[str]:
        images = []
        for root, _, files in os.walk(self.photos_dir):
            for f in files:
                if Path(f).suffix.lower() in SUPPORTED:
                    images.append(os.path.join(root, f))
        return sorted(images)

    def read_image(self, image_id: str) -> np.ndarray:
        img = cv2.imread(image_id)
        if img is None:
            raise ValueError(f"Could not read image: {image_id}")
        return img

    def get_display_url(self, image_id: str) -> str:
        rel = os.path.relpath(image_id, self.photos_dir)
        return f"/image/{rel.replace(os.sep, '/')}"
