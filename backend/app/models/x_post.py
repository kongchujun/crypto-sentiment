"""ORM model for the persisted X (Twitter) posts table.

Rows are uniquely identified by the X tweet id, which is what lets the
background fetcher upsert duplicates instead of inserting them twice. Engagement
counters (likes / retweets / replies / quotes) and `updated_at` are refreshed
on every re-fetch because those numbers grow over time.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class XPostRecord(Base):
    __tablename__ = "x_posts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    author_handle: Mapped[str] = mapped_column(String(64), nullable=False)
    author_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    likes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    retweets: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    replies: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    quotes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("ix_x_posts_symbol_created_at", "symbol", "created_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug only
        return f"<XPostRecord id={self.id} symbol={self.symbol} likes={self.likes}>"
