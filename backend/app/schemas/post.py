from __future__ import annotations

from pydantic import BaseModel, Field


class XPost(BaseModel):
    id: str
    author: str = Field(..., description="X handle, e.g. @whale_alert")
    content: str
    created_at: int = Field(..., description="Post creation time, epoch milliseconds (UTC)")
    likes: int = 0
    retweets: int = 0
    url: str | None = None
