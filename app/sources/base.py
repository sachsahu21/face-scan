from abc import ABC, abstractmethod
from typing import List
import numpy as np


class PhotoSource(ABC):
    @abstractmethod
    def list_images(self) -> List[str]:
        """Return list of image identifiers (file paths or cloud IDs)."""

    @abstractmethod
    def read_image(self, image_id: str) -> np.ndarray:
        """Read image and return as BGR numpy array (OpenCV format)."""

    @abstractmethod
    def get_display_url(self, image_id: str) -> str:
        """Return a URL the browser can use to display the image."""
