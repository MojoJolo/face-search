from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

from psycopg import connect
from psycopg.rows import dict_row


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/face_search")


@contextmanager
def get_db() -> Generator:
    with connect(DATABASE_URL, row_factory=dict_row) as conn:
        yield conn
