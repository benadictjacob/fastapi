from sqlalchemy.orm import Session
import models
from datetime import datetime
from typing import List, Optional
from sqlalchemy import desc

# ------------------------------
# Video Upload / Base Video
# ------------------------------
def create_video(db: Session, filename: str, duration: float, size: int):
    db_video = models.Video(
        filename=filename,
        duration=duration,
        size=size,
        upload_time=datetime.utcnow()
    )
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    return db_video

def get_videos(db: Session):
    return db.query(models.Video).all()

def get_video(db: Session, video_id: int):
    return db.query(models.Video).filter(models.Video.id == video_id).first()

def update_video(db: Session, video_id: int, filename: str = None, duration: float = None, size: int = None):
    """Update an existing video entry"""
    db_video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if db_video:
        if filename is not None:
            db_video.filename = filename
        if duration is not None:
            db_video.duration = duration
        if size is not None:
            db_video.size = size
        db.commit()
        db.refresh(db_video)
    return db_video

def delete_video(db: Session, video_id: int):
    """Delete a video and all associated records"""
    db_video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if db_video:
        # Delete all associated video qualities first
        db.query(models.VideoQuality).filter(
            models.VideoQuality.video_id == video_id
        ).delete()
        # Delete associated trimmed videos
        db.query(models.TrimmedVideo).filter(
            models.TrimmedVideo.video_id == video_id
        ).delete()
        # Delete associated overlay operations (cascading will handle detail tables)
        db.query(models.OverlayOperation).filter(
            models.OverlayOperation.base_video_id == video_id
        ).delete()
        
        db.delete(db_video)
        db.commit()
        return True
    return False


# ------------------------------
# Trimmed Video
# ------------------------------
def create_trimmed_video(db: Session, video_id: int, filename: str,
                         start_time: float, end_time: float,
                         duration: float, size: int):
    db_trimmed = models.TrimmedVideo(
        video_id=video_id,
        filename=filename,
        start_time=start_time,
        end_time=end_time,
        duration=duration,
        size=size,
        created_time=datetime.utcnow()
    )
    db.add(db_trimmed)
    db.commit()
    db.refresh(db_trimmed)
    return db_trimmed

def get_trimmed_videos(db: Session, video_id: int):
    return db.query(models.TrimmedVideo).filter(
        models.TrimmedVideo.video_id == video_id
    ).all()


# ------------------------------
# Overlay Operations (Master)
# ------------------------------
def create_overlay(db: Session, video_id: int, operation_type: str, filename: str):
    """Fix: Use 'filename' instead of 'output_filename' to match models.py"""
    overlay_op = models.OverlayOperation(
        base_video_id=video_id,
        filename=filename,  # corrected here
        operation_type=operation_type,
        created_time=datetime.utcnow()
    )
    db.add(overlay_op)
    db.commit()
    db.refresh(overlay_op)
    return overlay_op

def get_overlay_operations(db: Session, video_id: int):
    return db.query(models.OverlayOperation).filter(
        models.OverlayOperation.base_video_id == video_id
    ).all()


# ------------------------------
# Text Overlay
# ------------------------------
def create_text_overlay(db: Session, overlay_id: int, text: str, font_path: str, fontsize: int,
                        fontcolor: str, language: str, x: int, y: int,
                        start: float, end: float):
    text_overlay = models.TextOverlay(
        operation_id=overlay_id,
        text_content=text,
        font_path=font_path,
        font_size=fontsize,
        font_color=fontcolor,
        language=language,
        x_position=x,
        y_position=y,
        start_time=start,
        end_time=end
    )
    db.add(text_overlay)
    db.commit()
    db.refresh(text_overlay)
    return text_overlay

def get_text_overlays(db: Session, overlay_id: int):
    return db.query(models.TextOverlay).filter(
        models.TextOverlay.operation_id == overlay_id
    ).all()


# ------------------------------
# Image Overlay
# ------------------------------
def create_image_overlay(db: Session, overlay_id: int, image_path: str, x: int, y: int,
                         start: float, end: float):
    img_overlay = models.ImageOverlay(
        operation_id=overlay_id,
        image_path=image_path,
        x_position=x,
        y_position=y,
        start_time=start,
        end_time=end
    )
    db.add(img_overlay)
    db.commit()
    db.refresh(img_overlay)
    return img_overlay

def get_image_overlays(db: Session, overlay_id: int):
    return db.query(models.ImageOverlay).filter(
        models.ImageOverlay.operation_id == overlay_id
    ).all()


# ------------------------------
# Video Overlay
# ------------------------------
def create_video_overlay(db: Session, overlay_id: int, overlay_video_path: str, x: int, y: int,
                         start: float, end: float):
    video_overlay = models.VideoOverlay(
        operation_id=overlay_id,
        overlay_video_path=overlay_video_path,
        x_position=x,
        y_position=y,
        start_time=start,
        end_time=end
    )
    db.add(video_overlay)
    db.commit()
    db.refresh(video_overlay)
    return video_overlay

def get_video_overlays(db: Session, overlay_id: int):
    return db.query(models.VideoOverlay).filter(
        models.VideoOverlay.operation_id == overlay_id
    ).all()


# ------------------------------
# Watermark Overlay
# ------------------------------
def create_watermark(db: Session, overlay_id: int, watermark_path: str, x: int, y: int,
                     opacity: float):
    wm = models.Watermark(
        operation_id=overlay_id,
        watermark_path=watermark_path,
        x_position=x,
        y_position=y,
        opacity=opacity
    )
    db.add(wm)
    db.commit()
    db.refresh(wm)
    return wm

def get_watermarks(db: Session, overlay_id: int):
    return db.query(models.Watermark).filter(
        models.Watermark.operation_id == overlay_id
    ).all()


# ==========================
# NEW: Video Quality CRUD Operations
# ==========================

def create_video_quality(db: Session, video_id: int, quality: str, filename: str, 
                         bitrate: str = None, resolution: str = None, filesize: int = None):
    """Create a new video quality entry for a specific video"""
    db_quality = models.VideoQuality(
        video_id=video_id,
        quality=quality,
        filename=filename,
        bitrate=bitrate,
        resolution=resolution,
        filesize=filesize,
        created_time=datetime.utcnow()
    )
    db.add(db_quality)
    db.commit()
    db.refresh(db_quality)
    return db_quality

def create_multiple_video_qualities(db: Session, video_id: int, qualities_data: List[dict]):
    """Create multiple video quality entries at once
    
    Args:
        video_id: ID of the original video
        qualities_data: List of dictionaries containing quality data
                       [{'quality': '1080p', 'filename': 'file_1080p.mp4', 'bitrate': '5000k', ...}, ...]
    """
    db_qualities = []
    for quality_data in qualities_data:
        db_quality = models.VideoQuality(
            video_id=video_id,
            created_time=datetime.utcnow(),
            **quality_data
        )
        db.add(db_quality)
        db_qualities.append(db_quality)
    
    db.commit()
    for db_quality in db_qualities:
        db.refresh(db_quality)
    return db_qualities

def get_video_qualities(db: Session, video_id: int):
    """Get all quality versions for a specific video, ordered by filesize (highest first)"""
    return db.query(models.VideoQuality).filter(
        models.VideoQuality.video_id == video_id
    ).order_by(desc(models.VideoQuality.filesize)).all()

def get_video_by_quality(db: Session, video_id: int, quality: str):
    """Get a specific quality version of a video"""
    return db.query(models.VideoQuality).filter(
        models.VideoQuality.video_id == video_id,
        models.VideoQuality.quality == quality
    ).first()

def get_quality_by_id(db: Session, quality_id: int):
    """Get video quality by its ID"""
    return db.query(models.VideoQuality).filter(
        models.VideoQuality.id == quality_id
    ).first()

def get_available_qualities(db: Session, video_id: int) -> List[str]:
    """Get list of available quality options for a video"""
    qualities = db.query(models.VideoQuality.quality).filter(
        models.VideoQuality.video_id == video_id
    ).distinct().all()
    return [quality[0] for quality in qualities]

def update_video_quality(db: Session, quality_id: int, quality: str = None, filename: str = None,
                        bitrate: str = None, resolution: str = None, filesize: int = None):
    """Update a specific video quality entry"""
    db_quality = db.query(models.VideoQuality).filter(
        models.VideoQuality.id == quality_id
    ).first()
    
    if db_quality:
        if quality is not None:
            db_quality.quality = quality
        if filename is not None:
            db_quality.filename = filename
        if bitrate is not None:
            db_quality.bitrate = bitrate
        if resolution is not None:
            db_quality.resolution = resolution
        if filesize is not None:
            db_quality.filesize = filesize
        db.commit()
        db.refresh(db_quality)
    return db_quality

def delete_video_quality(db: Session, quality_id: int):
    """Delete a specific video quality entry"""
    db_quality = db.query(models.VideoQuality).filter(
        models.VideoQuality.id == quality_id
    ).first()
    
    if db_quality:
        db.delete(db_quality)
        db.commit()
        return True
    return False

# ==========================
# Utility Functions for Video Quality Management
# ==========================

def get_video_with_qualities(db: Session, video_id: int):
    """Get video with all its quality versions"""
    return db.query(models.Video).filter(
        models.Video.id == video_id
    ).first()

def quality_exists(db: Session, video_id: int, quality: str) -> bool:
    """Check if a specific quality already exists for a video"""
    return db.query(models.VideoQuality).filter(
        models.VideoQuality.video_id == video_id,
        models.VideoQuality.quality == quality
    ).first() is not None

def get_best_quality(db: Session, video_id: int):
    """Get the highest quality version available for a video (by filesize)"""
    return db.query(models.VideoQuality).filter(
        models.VideoQuality.video_id == video_id
    ).order_by(desc(models.VideoQuality.filesize)).first()

def get_video_stats(db: Session, video_id: int) -> Optional[dict]:
    """Get comprehensive stats for a video including all qualities"""
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not video:
        return None
    
    qualities = get_video_qualities(db, video_id)
    trimmed_count = db.query(models.TrimmedVideo).filter(
        models.TrimmedVideo.video_id == video_id
    ).count()
    overlay_count = db.query(models.OverlayOperation).filter(
        models.OverlayOperation.base_video_id == video_id
    ).count()
    
    return {
        'video_id': video.id,
        'filename': video.filename,
        'original_duration': video.duration,
        'original_size': video.size,
        'upload_time': video.upload_time,
        'available_qualities': [q.quality for q in qualities],
        'total_qualities': len(qualities),
        'trimmed_versions': trimmed_count,
        'overlay_operations': overlay_count,
        'quality_details': [
            {
                'id': q.id,
                'quality': q.quality,
                'filename': q.filename,
                'bitrate': q.bitrate,
                'resolution': q.resolution,
                'filesize': q.filesize,
                'created_time': q.created_time
            } for q in qualities
        ]
    }

def get_quality_download_info(db: Session, video_id: int, quality: str) -> Optional[dict]:
    """Get download information for a specific quality"""
    quality_info = get_video_by_quality(db, video_id, quality)
    if not quality_info:
        return None
    
    video = get_video(db, video_id)
    return {
        'quality_id': quality_info.id,
        'video_id': video_id,
        'original_video_filename': video.filename,
        'quality': quality_info.quality,
        'filename': quality_info.filename,
        'bitrate': quality_info.bitrate,
        'resolution': quality_info.resolution,
        'filesize': quality_info.filesize,
        'created_time': quality_info.created_time
    }