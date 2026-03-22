"""
Pydantic request/response models for all API endpoints.
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict


# ──────────────────────────── Tags ────────────────────────────

class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str
    video_count: Optional[int] = None


class TagCreate(BaseModel):
    name: str
    color: str = "#6366f1"


class TagUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None


# ──────────────────────────── Videos ────────────────────────────

class VideoListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    video_id: str
    video_title: str
    video_url: str
    channel_name: Optional[str] = None
    channel_url: Optional[str] = None
    last_watched: Optional[str] = None
    watch_count: int = 1
    watchlist_status: Optional[str] = None
    tags: list[str] = []
    has_transcript: bool = False


class VideoListResponse(BaseModel):
    total: int
    page: int
    per_page: int
    videos: list[VideoListItem]


class WatchEntry(BaseModel):
    watched_at: str


class VideoDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    video_id: str
    video_title: str
    video_url: str
    channel_name: Optional[str] = None
    channel_url: Optional[str] = None
    watch_history: list[WatchEntry] = []
    watch_count: int = 1
    tags: list[TagOut] = []
    watchlist: Optional[WatchlistItem] = None
    notes: Optional[str] = None
    transcript: Optional[TranscriptOut] = None


class VideoCreate(BaseModel):
    video_id: str
    video_title: str
    video_url: str
    channel_name: Optional[str] = None
    channel_url: Optional[str] = None
    watched_at: str
    tags: list[str] = []
    watchlist_status: Optional[str] = None
    notes: Optional[str] = None
    fetch_transcript: bool = False


class SetTagsRequest(BaseModel):
    tag_ids: list[int]


# ──────────────────────────── Watchlist ────────────────────────────

class WatchlistItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    video_id: str
    status: str
    notes: Optional[str] = None
    priority: int = 0
    added_at: Optional[str] = None
    updated_at: Optional[str] = None
    video_title: Optional[str] = None
    channel_name: Optional[str] = None
    video_url: Optional[str] = None
    tags: list[str] = []


class WatchlistCreate(BaseModel):
    video_id: str
    status: str = "to-rewatch"
    notes: Optional[str] = None
    priority: int = 0


class WatchlistUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    priority: Optional[int] = None


# ──────────────────────────── Transcripts ────────────────────────────

class TranscriptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    video_id: str
    transcript: str
    language: Optional[str] = None
    fetched_at: Optional[str] = None


# ──────────────────────────── Notes ────────────────────────────

class NotesOut(BaseModel):
    video_id: str
    content: str
    updated_at: Optional[str] = None


class NotesUpsert(BaseModel):
    content: str


# ──────────────────────────── Stats ────────────────────────────

class TopChannel(BaseModel):
    channel_name: str
    watch_count: int


class StatsOut(BaseModel):
    total_videos: int
    unique_videos: int
    total_channels: int
    total_tags: int
    watchlist_count: int
    transcript_count: int
    rewatched_count: int
    top_channels: list[TopChannel]
    watchlist_by_status: dict[str, int]
    watches_by_hour: dict[str, int]
