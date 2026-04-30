from __future__ import annotations

from typing import Any

from psycopg import Connection

from app.ingest import format_vector
from app.insightface_service import get_face_analyzer


def search_similar_faces(
    conn: Connection,
    image,
    top_k: int,
    threshold: float | None,
) -> list[dict[str, Any]]:
    analyzer = get_face_analyzer()
    faces = analyzer.get(image)

    if not faces:
        raise ValueError("No face detected in uploaded image")

    if len(faces) > 1:
        raise ValueError("Upload must contain exactly one face")

    query_face = faces[0]
    embedding = query_face.normed_embedding.astype(float).tolist()
    vector = format_vector(embedding)

    sql = """
        select
          images.file_path,
          faces.bbox_x1,
          faces.bbox_y1,
          faces.bbox_x2,
          faces.bbox_y2,
          faces.det_score,
          faces.embedding <=> %s::vector as distance
        from faces
        join images on faces.image_id = images.id
        order by faces.embedding <=> %s::vector
        limit %s
    """

    with conn.cursor() as cur:
        cur.execute(sql, (vector, vector, top_k))
        rows = cur.fetchall()

    results = []
    for row in rows:
        similarity = 1 - float(row["distance"])
        if threshold is not None and similarity < threshold:
            continue
        results.append(
            {
                "image_path": row["file_path"],
                "bbox": {
                    "x1": row["bbox_x1"],
                    "y1": row["bbox_y1"],
                    "x2": row["bbox_x2"],
                    "y2": row["bbox_y2"],
                },
                "distance": float(row["distance"]),
                "similarity": similarity,
                "det_score": row["det_score"],
            }
        )

    return results
