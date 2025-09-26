# models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    duration = Column(Float, nullable=True)
    size = Column(Integer, nullable=True)
    upload_time = Column(DateTime, default=datetime.utcnow)

    # relationships
    trims = relationship(
        "TrimmedVideo",
        back_populates="original_video",
        cascade="all, delete-orphan",
    )

    # Overlay operations that use this video as the base video
    overlay_operations = relationship(
        "OverlayOperation",
        back_populates="base_video",
        cascade="all, delete-orphan",
    )

    # NEW: Relationship for video qualities
    qualities = relationship(
        "VideoQuality",
        back_populates="original_video",
        cascade="all, delete-orphan",
    )


class TrimmedVideo(Base):
    __tablename__ = "trimmed_videos"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"))
    filename = Column(String, nullable=False)
    duration = Column(Float, nullable=True)
    size = Column(Integer, nullable=True)
    start_time = Column(Float, nullable=True)
    end_time = Column(Float, nullable=True)
    created_time = Column(DateTime, default=datetime.utcnow)

    original_video = relationship("Video", back_populates="trims")


# --- Overlay detail tables (define before the OverlayOperation mapper) ---

class TextOverlay(Base):
    """Stores configuration for text overlay operations"""
    __tablename__ = "text_overlays"

    id = Column(Integer, primary_key=True, index=True)
    operation_id = Column(Integer, ForeignKey("overlay_operations.id"))
    text_content = Column(Text, nullable=False)
    font_path = Column(String, nullable=False)
    font_size = Column(Integer, default=30)
    font_color = Column(String, default="white")
    language = Column(String, default="en")
    x_position = Column(Integer, default=100)
    y_position = Column(Integer, default=50)
    start_time = Column(Float, default=0.0)
    end_time = Column(Float, nullable=True)

    operation = relationship("OverlayOperation", back_populates="text_overlay")


class ImageOverlay(Base):
    """Stores configuration for image overlay operations"""
    __tablename__ = "image_overlays"

    id = Column(Integer, primary_key=True, index=True)
    operation_id = Column(Integer, ForeignKey("overlay_operations.id"))
    image_path = Column(String, nullable=False)
    x_position = Column(Integer, default=0)
    y_position = Column(Integer, default=0)
    start_time = Column(Float, default=0.0)
    end_time = Column(Float, nullable=True)

    operation = relationship("OverlayOperation", back_populates="image_overlay")


class VideoOverlay(Base):
    """Stores configuration for video-on-video overlay operations"""
    __tablename__ = "video_overlays"

    id = Column(Integer, primary_key=True, index=True)
    operation_id = Column(Integer, ForeignKey("overlay_operations.id"))
    overlay_video_path = Column(String, nullable=False)
    x_position = Column(Integer, default=0)
    y_position = Column(Integer, default=0)
    start_time = Column(Float, default=0.0)
    end_time = Column(Float, nullable=True)

    operation = relationship("OverlayOperation", back_populates="video_overlay")


class Watermark(Base):
    """Stores configuration for watermark operations"""
    __tablename__ = "watermarks"

    id = Column(Integer, primary_key=True, index=True)
    operation_id = Column(Integer, ForeignKey("overlay_operations.id"))
    watermark_path = Column(String, nullable=False)
    x_position = Column(Integer, default=0)
    y_position = Column(Integer, default=0)
    opacity = Column(Float, default=0.5)

    operation = relationship("OverlayOperation", back_populates="watermark")


# --- Master overlay operation table that ties everything together ---
class OverlayOperation(Base):
    """Main table to track any overlay operation performed on a video"""
    __tablename__ = "overlay_operations"

    id = Column(Integer, primary_key=True, index=True)
    base_video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    filename = Column(String, nullable=False)            # output filename
    operation_type = Column(String, nullable=False)      # 'text', 'image', 'video', 'watermark'
    duration = Column(Float, nullable=True)              # duration of the output file (seconds)
    size = Column(Integer, nullable=True)                # size in bytes
    created_time = Column(DateTime, default=datetime.utcnow)

    # relationships to detailed config rows (one-to-one)
    base_video = relationship("Video", back_populates="overlay_operations")

    text_overlay = relationship(
        "TextOverlay",
        back_populates="operation",
        uselist=False,
        cascade="all, delete-orphan",
    )

    image_overlay = relationship(
        "ImageOverlay",
        back_populates="operation",
        uselist=False,
        cascade="all, delete-orphan",
    )

    video_overlay = relationship(
        "VideoOverlay",
        back_populates="operation",
        uselist=False,
        cascade="all, delete-orphan",
    )

    watermark = relationship(
        "Watermark",
        back_populates="operation",
        uselist=False,
        cascade="all, delete-orphan",
    )


# ==========================
# NEW: Video Quality Model
# ==========================

class VideoQuality(Base):
    """Stores different quality versions of a video"""
    __tablename__ = "video_qualities"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    quality = Column(String, nullable=False, index=True)  # 'original', '1080p', '720p', '480p'
    filename = Column(String, nullable=False)
    bitrate = Column(String, nullable=True)
    resolution = Column(String, nullable=True)
    filesize = Column(Integer, nullable=True)
    created_time = Column(DateTime, default=datetime.utcnow)

    # Relationship back to the original video
    original_video = relationship("Video", back_populates="qualities")