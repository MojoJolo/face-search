from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.db import get_db
from app.ingest import ingest_folder, ingest_uploaded_files
from app.insightface_service import decode_image, ensure_rgb
from app.search import search_similar_faces


router = APIRouter()
PHOTOS_ROOT = os.getenv("PHOTOS_ROOT", "/data/photos")


class IngestRequest(BaseModel):
    folder_path: str = Field(default=PHOTOS_ROOT)
    recursive: bool = True
    min_face_size: int = 80
    det_threshold: float = 0.6
    max_faces: int = 20


@router.get("/health")
def healthcheck() -> dict:
    return {"status": "ok"}


@router.post("/ingest")
def ingest_images(payload: IngestRequest) -> dict:
    folder = Path(payload.folder_path)
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=400, detail="Folder path does not exist or is not a directory")

    with get_db() as conn:
        try:
            return ingest_folder(
                conn=conn,
                folder_path=payload.folder_path,
                recursive=payload.recursive,
                min_face_size=payload.min_face_size,
                det_threshold=payload.det_threshold,
                max_faces=payload.max_faces,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ingest-upload")
async def ingest_uploaded_images(
    files: list[UploadFile] = File(...),
    min_face_size: int = Form(default=80),
    det_threshold: float = Form(default=0.6),
    max_faces: int = Form(default=20),
) -> dict:
    file_data = [(upload.filename or "upload", await upload.read()) for upload in files]

    with get_db() as conn:
        try:
            return ingest_uploaded_files(
                conn=conn,
                files=file_data,
                upload_dir=PHOTOS_ROOT,
                min_face_size=min_face_size,
                det_threshold=det_threshold,
                max_faces=max_faces,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


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
