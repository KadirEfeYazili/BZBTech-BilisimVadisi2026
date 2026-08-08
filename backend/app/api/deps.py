"""API bağımlılıkları."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db


def db_session() -> Iterator[Session]:
    """İstek başına veritabanı oturumu üretir."""
    yield from get_db()


DbSession = Annotated[Session, Depends(db_session)]
