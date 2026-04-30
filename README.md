# Face Search

Minimal local prototype for face ingest and selfie search using InsightFace, FastAPI, PostgreSQL, and pgvector.

## Run

```bash
cd face-search
docker compose up --build
```

Open `http://localhost:5175`.

## Notes

- Put images in `./photos`, which is mounted into the backend at `/data/photos`.
- The first InsightFace run will download the `buffalo_l` model into the Docker volume mounted at `/root/.insightface`.
- Backend API is available at `http://localhost:8001`.
