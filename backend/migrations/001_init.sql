create extension if not exists vector;

create table if not exists images (
  id uuid primary key,
  file_path text unique,
  created_at timestamptz default now()
);

create table if not exists faces (
  id uuid primary key,
  image_id uuid references images(id),
  bbox_x1 int,
  bbox_y1 int,
  bbox_x2 int,
  bbox_y2 int,
  det_score real,
  embedding vector(512),
  created_at timestamptz default now()
);

create index if not exists faces_embedding_idx
on faces
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);
