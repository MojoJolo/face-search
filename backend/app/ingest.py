from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from psycopg import Connection

from app.insightface_service import decode_image, ensure_rgb, get_face_analyzer


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def iter_image_paths(folder_path: str, recursive: bool) -> Iterable[Path]:
    base = Path(folder_path)
    pattern = "**/*" if recursive else "*"
    for path in sorted(base.glob(pattern)):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            yield path


def format_vector(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.10f}" for value in values) + "]"


def ingest_folder(
    conn: Connection,
    folder_path: str,
    recursive: bool,
    min_face_size: int,
    det_threshold: float,
    max_faces: int,
) -> dict:
    analyzer = get_face_analyzer()
    image_count = 0
    face_count = 0
    preview_images: list[dict] = []
    skipped_files: list[dict] = []

    for image_path in iter_image_paths(folder_path, recursive):
        image_count += 1
        image_bytes = image_path.read_bytes()
        mime_type, _ = mimetypes.guess_type(str(image_path))
        if mime_type is None or not mime_type.startswith("image/"):
            skipped_files.append({"file_path": str(image_path), "reason": "unsupported mime type"})
            continue

        try:
            image = ensure_rgb(decode_image(image_bytes))
        except ValueError as exc:
            skipped_files.append({"file_path": str(image_path), "reason": str(exc)})
            continue

        analyzer.det_model.det_thresh = det_threshold

        faces = analyzer.get(image, max_num=max_faces)

        filtered_faces = []
        for face in faces:
            bbox = [int(value) for value in face.bbox]
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            if min(width, height) < min_face_size:
                continue
            filtered_faces.append(
                {
                    "bbox": {
                        "x1": bbox[0],
                        "y1": bbox[1],
                        "x2": bbox[2],
                        "y2": bbox[3],
                    },
                    "det_score": float(face.det_score),
                    "embedding": face.normed_embedding.astype(float).tolist(),
                }
            )

        image_id = uuid4()
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into images (id, file_path)
                values (%s, %s)
                on conflict (file_path) do update
                  set file_path = excluded.file_path
                returning id
                """,
                (image_id, str(image_path.resolve())),
            )
            stored_image_id = cur.fetchone()["id"]
            cur.execute("delete from faces where image_id = %s", (stored_image_id,))

            if not filtered_faces:
                skipped_files.append({"file_path": str(image_path), "reason": "no faces matched filters"})
                continue

            for face_data in filtered_faces:
                bbox = face_data["bbox"]
                cur.execute(
                    """
                    insert into faces (
                      id, image_id, bbox_x1, bbox_y1, bbox_x2, bbox_y2, det_score, embedding
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s::vector)
                    """,
                    (
                        uuid4(),
                        stored_image_id,
                        bbox["x1"],
                        bbox["y1"],
                        bbox["x2"],
                        bbox["y2"],
                        face_data["det_score"],
                        format_vector(face_data["embedding"]),
                    ),
                )

        preview_images.append(
            {
                "image_path": str(image_path.resolve()),
                "faces": [
                    {"bbox": face_data["bbox"], "det_score": face_data["det_score"]}
                    for face_data in filtered_faces
                ],
            }
        )
        face_count += len(filtered_faces)

    conn.commit()
    return {
        "images_processed": image_count,
        "faces_stored": face_count,
        "preview_images": preview_images,
        "skipped_files": skipped_files,
    }
