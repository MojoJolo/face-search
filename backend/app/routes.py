from __future__ import annotations

import os
import threading
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.db import get_db
from app.ingest import ingest_folder, ingest_uploaded_files
from app.insightface_service import decode_image, ensure_rgb
from app.jobs import JobStatus, create_job, get_job
from app.search import search_similar_faces


router = APIRouter()
PHOTOS_ROOT = os.getenv("PHOTOS_ROOT", "/data/photos")


class IngestRequest(BaseModel):
    folder_path: str = Field(default=PHOTOS_ROOT)
    recursive: bool = True
    min_face_size: int = 80
    det_threshold: float = 0.6
    max_faces: int = 20


def _run_folder_ingest(job, payload: IngestRequest) -> None:
    try:
        with get_db() as conn:
            ingest_folder(
                conn=conn,
                folder_path=payload.folder_path,
                recursive=payload.recursive,
                min_face_size=payload.min_face_size,
                det_threshold=payload.det_threshold,
                max_faces=payload.max_faces,
                job=job,
            )
    except Exception as exc:
        job.status = JobStatus.FAILED
        job.error = str(exc)


def _run_upload_ingest(job, file_data, min_face_size, det_threshold, max_faces) -> None:
    try:
        with get_db() as conn:
            ingest_uploaded_files(
                conn=conn,
                files=file_data,
                upload_dir=PHOTOS_ROOT,
                min_face_size=min_face_size,
                det_threshold=det_threshold,
                max_faces=max_faces,
                job=job,
            )
    except Exception as exc:
        job.status = JobStatus.FAILED
        job.error = str(exc)


@router.get("/health")
def healthcheck() -> dict:
    return {"status": "ok"}


@router.post("/ingest")
def ingest_images(payload: IngestRequest) -> dict:
    folder = Path(payload.folder_path)
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=400, detail="Folder path does not exist or is not a directory")

    job = create_job()
    thread = threading.Thread(target=_run_folder_ingest, args=(job, payload), daemon=True)
    thread.start()
    return {"job_id": job.id}


@router.post("/ingest-upload")
async def ingest_uploaded_images(
    files: list[UploadFile] = File(...),
    min_face_size: int = Form(default=80),
    det_threshold: float = Form(default=0.6),
    max_faces: int = Form(default=20),
) -> dict:
    file_data = [(upload.filename or "upload", await upload.read()) for upload in files]

    job = create_job()
    thread = threading.Thread(
        target=_run_upload_ingest,
        args=(job, file_data, min_face_size, det_threshold, max_faces),
        daemon=True,
    )
    thread.start()
    return {"job_id": job.id}


@router.get("/ingest-status/{job_id}")
def ingest_status(job_id: str) -> dict:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()


@router.get("/ingested-images")
def ingested_images(limit: int = 50, offset: int = 0) -> dict:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select i.id, i.file_path, i.created_at,
                       json_agg(json_build_object(
                           'bbox', json_build_object(
                               'x1', f.bbox_x1, 'y1', f.bbox_y1,
                               'x2', f.bbox_x2, 'y2', f.bbox_y2
                           ),
                           'det_score', f.det_score
                       )) as faces
                from images i
                join faces f on f.image_id = i.id
                group by i.id
                order by i.created_at desc
                limit %s offset %s
                """,
                (limit, offset),
            )
            rows = cur.fetchall()

            cur.execute("select count(*) as total from images i where exists (select 1 from faces f where f.image_id = i.id)")
            total = cur.fetchone()["total"]

    images = [
        {
            "image_path": row["file_path"],
            "faces": row["faces"],
            "created_at": row["created_at"].isoformat(),
        }
        for row in rows
    ]
    return {"images": images, "total": total}


@router.post("/search")
async def search_faces(
    file: UploadFile = File(...),
    top_k: int = Form(default=10),
    threshold: float = Form(default=0.0),
) -> dict:
    image_bytes = await file.read()
    try:
        image = ensure_rgb(decode_image(image_bytes))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    with get_db() as conn:
        try:
            results = search_similar_faces(conn, image, top_k=top_k, threshold=threshold)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"results": results, "count": len(results)}


@router.get("/image-preview")
def image_preview(path: str) -> FileResponse:
    image_path = Path(path).expanduser().resolve()
    if not image_path.exists() or not image_path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")

    mime_type = image_path.suffix.lower()
    if mime_type not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
        raise HTTPException(status_code=400, detail="Unsupported image type")

    return FileResponse(image_path)
