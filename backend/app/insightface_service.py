from __future__ import annotations

import os
from functools import lru_cache

import cv2
import numpy as np
from insightface.app import FaceAnalysis


MODEL_NAME = os.getenv("INSIGHTFACE_MODEL_NAME", "buffalo_l")
CTX_ID = int(os.getenv("INSIGHTFACE_CTX_ID", "-1"))


@lru_cache(maxsize=1)
def get_face_analyzer() -> FaceAnalysis:
    app = FaceAnalysis(name=MODEL_NAME)
    app.prepare(ctx_id=CTX_ID)
    return app


def decode_image(image_bytes: bytes) -> np.ndarray:
    np_buffer = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(np_buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Unable to decode image")
    return image


def ensure_rgb(image: np.ndarray) -> np.ndarray:
    if len(image.shape) == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    return image
