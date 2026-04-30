from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from psycopg import Connection

from app.insightface_service import decode_image, ensure_rgb, get_face_analyzer
from app.jobs import Job, JobStatus


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def _process_image(
    conn: Connection,
    image_path: Path,
    image_bytes: bytes,
    original_name: str,
    analyzer,
    min_face_size: int,
    det_threshold: float,
    max_faces: int,
    skipped_files: list[dict],
    preview_images: list[dict],
) -> int:
    """Process a single image. Returns number of faces stored."""
    try:
        image = ensure_rgb(decode_image(image_bytes))
    except ValueError as exc:
        skipped_files.append({"file_path": original_name, "reason": str(exc)})
        return 0

    analyzer.det_model.det_thresh = det_threshold
    faces = analyzer.get(image, max_num=max_faces)

    filtered_faces = []
    for face in faces:
        bbox = [int(v) for v in face.bbox]
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        if min(width, height) < min_face_size:
            continue
        filtered_faces.append(
            {
                "bbox": {"x1": bbox[0], "y1": bbox[1], "x2": bbox[2], "y2": bbox[3]},
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
            skipped_files.append({"file_path": original_name, "reason": "no faces matched filters"})
            return 0

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
            "faces": [{"bbox": fd["bbox"], "det_score": fd["det_score"]} for fd in filtered_faces],
        }
    )
    return len(filtered_faces)


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
    job: Job,
) -> None:
    analyzer = get_face_analyzer()

    image_paths = list(iter_image_paths(folder_path, recursive))
    job.images_total = len(image_paths)
    job.status = JobStatus.RUNNING

    for image_path in image_paths:
        job.current_file = str(image_path)
        image_bytes = image_path.read_bytes()
        mime_type, _ = mimetypes.guess_type(str(image_path))
        if mime_type is None or not mime_type.startswith("image/"):
            job.skipped_files.append({"file_path": str(image_path), "reason": "unsupported mime type"})
            job.images_processed += 1
            continue

        faces = _process_image(
            conn=conn,
            image_path=image_path,
            image_bytes=image_bytes,
            original_name=str(image_path),
            analyzer=analyzer,
            min_face_size=min_face_size,
            det_threshold=det_threshold,
            max_faces=max_faces,
            skipped_files=job.skipped_files,
            preview_images=job.preview_images,
        )
        job.faces_stored += faces
        job.images_processed += 1

    conn.commit()
    job.current_file = ""
    job.status = JobStatus.COMPLETED


def ingest_uploaded_files(
    conn: Connection,
    files: list[tuple[str, bytes]],
    upload_dir: str,
    min_face_size: int,
    det_threshold: float,
    max_faces: int,
    job: Job,
) -> None:
    analyzer = get_face_analyzer()
    upload_path = Path(upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)

    job.images_total = len(files)
    job.status = JobStatus.RUNNING

    for original_name, image_bytes in files:
        suffix = Path(original_name).suffix.lower()
        if suffix not in IMAGE_EXTENSIONS:
            job.skipped_files.append({"file_path": original_name, "reason": "unsupported file type"})
            job.images_processed += 1
            continue

        saved_path = upload_path / f"{uuid4().hex}_{Path(original_name).name}"
        saved_path.write_bytes(image_bytes)

        job.current_file = original_name
        faces = _process_image(
            conn=conn,
            image_path=saved_path,
            image_bytes=image_bytes,
            original_name=original_name,
            analyzer=analyzer,
            min_face_size=min_face_size,
            det_threshold=det_threshold,
            max_faces=max_faces,
            skipped_files=job.skipped_files,
            preview_images=job.preview_images,
        )
        job.faces_stored += faces
        job.images_processed += 1

    conn.commit()
    job.current_file = ""
    job.status = JobStatus.COMPLETED
