import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from app.core.config import settings


def _engine_kwargs() -> dict:
    url = settings.database_url
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    # Neon (free PostgreSQL cloud) — ensure SSL
    if "neon.tech" in url and "sslmode=" not in url:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}sslmode=require"
        return {"url": url, "pool_pre_ping": True}
    return {"pool_pre_ping": True}


_kwargs = _engine_kwargs()
_db_url = _kwargs.pop("url", settings.database_url)
engine = create_engine(_db_url, **_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def generate_uuid() -> str:
    return uuid.uuid4().hex


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    meetings: Mapped[list["Meeting"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(500), default="Untitled Meeting")
    platform: Mapped[str] = mapped_column(String(50), default="unknown")
    status: Mapped[str] = mapped_column(String(50), default="detecting", index=True)
    progress_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    share_token: Mapped[str] = mapped_column(String(64), unique=True, default=generate_uuid)
    meeting_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    meeting_mode: Mapped[str | None] = mapped_column(String(50), nullable=True)
    series_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    use_rag: Mapped[bool] = mapped_column(Boolean, default=False)
    rag_context_used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="meetings")
    recording: Mapped["Recording | None"] = relationship(back_populates="meeting", uselist=False, cascade="all, delete-orphan")
    transcript: Mapped["Transcript | None"] = relationship(back_populates="meeting", uselist=False, cascade="all, delete-orphan")
    summary: Mapped["Summary | None"] = relationship(back_populates="meeting", uselist=False, cascade="all, delete-orphan")
    action_items: Mapped[list["ActionItem"]] = relationship(back_populates="meeting", cascade="all, delete-orphan")
    participants: Mapped[list["Participant"]] = relationship(back_populates="meeting", cascade="all, delete-orphan")


class Recording(Base):
    __tablename__ = "recordings"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), unique=True)
    s3_key: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(100), default="audio/webm")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    meeting: Mapped["Meeting"] = relationship(back_populates="recording")


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), unique=True)
    full_text: Mapped[str] = mapped_column(Text, default="")
    segments_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    meeting: Mapped["Meeting"] = relationship(back_populates="transcript")


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), unique=True)
    executive_summary: Mapped[str] = mapped_column(Text, default="")
    detailed_summary: Mapped[str] = mapped_column(Text, default="")
    bullet_summary: Mapped[list] = mapped_column(JSON, default=list)
    key_decisions: Mapped[list] = mapped_column(JSON, default=list)
    discussion_points: Mapped[list] = mapped_column(JSON, default=list)
    open_questions: Mapped[list] = mapped_column(JSON, default=list)
    risks: Mapped[list] = mapped_column(JSON, default=list)
    next_steps: Mapped[list] = mapped_column(JSON, default=list)
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    meeting: Mapped["Meeting"] = relationship(back_populates="summary")


class ActionItem(Base):
    __tablename__ = "action_items"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), index=True)
    task: Mapped[str] = mapped_column(Text)
    owner: Mapped[str] = mapped_column(String(255), default="Unassigned")
    deadline: Mapped[str] = mapped_column(String(255), default="Not specified")
    status: Mapped[str] = mapped_column(String(50), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    meeting: Mapped["Meeting"] = relationship(back_populates="action_items")


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    meeting: Mapped["Meeting"] = relationship(back_populates="participants")


def init_db() -> None:
    from sqlalchemy import text

    Base.metadata.create_all(bind=engine)
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE meetings ADD COLUMN IF NOT EXISTS meeting_mode VARCHAR(50)"))
            conn.execute(text("ALTER TABLE meetings ADD COLUMN IF NOT EXISTS series_id VARCHAR(255)"))
            conn.execute(text("ALTER TABLE meetings ADD COLUMN IF NOT EXISTS use_rag BOOLEAN DEFAULT FALSE"))
            conn.execute(text("ALTER TABLE meetings ADD COLUMN IF NOT EXISTS rag_context_used BOOLEAN DEFAULT FALSE"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
