from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import subprocess, os, json, shutil, uuid
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel

import crud, models, database
from database import SessionLocal, engine, Base

# ==========================
# DB setup
# ==========================
# Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

# ==========================
# FastAPI app
# ==========================
app = FastAPI()

# ==========================
# FFmpeg paths
# ==========================
FFMPEG_PATH = r"C:\Users\VICTUS\ffmpeg\ffmpeg.exe"
FFPROBE_PATH = r"C:\Users\VICTUS\ffmpeg\ffprobe.exe"

# ==========================
# Directories
# ==========================
TEMP_DIR = "./temp_uploads"
PROCESSED_DIR = "./processed"
QUALITIES_DIR = "./qualities"  # NEW: Directory for quality versions
Path(TEMP_DIR).mkdir(parents=True, exist_ok=True)
Path(PROCESSED_DIR).mkdir(parents=True, exist_ok=True)
Path(QUALITIES_DIR).mkdir(parents=True, exist_ok=True)  # NEW

# ==========================
# NEW: Pydantic Models for Video Quality
# ==========================
class QualityGenerationRequest(BaseModel):
    qualities: List[str] = ["1080p", "720p", "480p"]

class VideoQualityResponse(BaseModel):
    id: int
    video_id: int
    quality: str
    filename: str
    bitrate: Optional[str]
    resolution: Optional[str]
    filesize: Optional[int]

# ==========================
# DB dependency
# ==========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================
# NEW: Video Quality Processing Functions
# ==========================
def get_video_metadata(video_path: str) -> dict:
    """Get video metadata using ffprobe"""
    cmd = [
        FFPROBE_PATH, "-v", "error", 
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,bit_rate:format=duration,size,bit_rate",
        "-of", "json", video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout)

def generate_video_quality(input_path: str, output_path: str, quality: str) -> dict:
    """Generate a specific quality version of a video"""
    quality_settings = {
        "1080p": {"resolution": "1920x1080", "bitrate": "5000k", "crf": "23"},
        "720p": {"resolution": "1280x720", "bitrate": "2500k", "crf": "25"},
        "480p": {"resolution": "854x480", "bitrate": "1000k", "crf": "28"},
    }
    
    if quality not in quality_settings:
        raise ValueError(f"Unsupported quality: {quality}")
    
    settings = quality_settings[quality]
    
    cmd = [
        FFMPEG_PATH, "-i", input_path,
        "-vf", f"scale={settings['resolution']}",
        "-b:v", settings["bitrate"],
        "-crf", settings["crf"],
        "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k",
        output_path
    ]
    
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    
    # Get metadata of generated file
    metadata = get_video_metadata(output_path)
    filesize = os.path.getsize(output_path)
    
    return {
        "resolution": settings["resolution"],
        "bitrate": settings["bitrate"],
        "filesize": filesize
    }

def process_video_qualities(video_id: int, original_filename: str, qualities: List[str], db: Session):
    """Background task to process video qualities"""
    try:
        input_path = os.path.join(TEMP_DIR, original_filename)
        qualities_data = []
        
        for quality in qualities:
            output_filename = f"{quality}_{uuid.uuid4().hex}.mp4"
            output_path = os.path.join(QUALITIES_DIR, output_filename)
            
            try:
                metadata = generate_video_quality(input_path, output_path, quality)
                qualities_data.append({
                    "quality": quality,
                    "filename": output_filename,
                    "bitrate": metadata["bitrate"],
                    "resolution": metadata["resolution"],
                    "filesize": metadata["filesize"]
                })
            except Exception as e:
                print(f"Failed to generate {quality} for video {video_id}: {str(e)}")
                continue
        
        # Save to database
        if qualities_data:
            crud.create_multiple_video_qualities(db, video_id, qualities_data)
            print(f"Successfully generated {len(qualities_data)} quality versions for video {video_id}")
    
    except Exception as e:
        print(f"Error processing qualities for video {video_id}: {str(e)}")

# ==========================
# Cleanup database
# ==========================
def cleanup_database():
    db = SessionLocal()
    try:
        videos = db.query(models.Video).all()
        for video in videos:
            current_path = os.path.join(TEMP_DIR, video.filename)
            if not os.path.exists(current_path):
                for file in os.listdir(TEMP_DIR):
                    if file.endswith(video.filename) or video.filename in file:
                        video.filename = file
                        break
        db.commit()
    except Exception as e:
        print(f"Cleanup error: {e}")
    finally:
        db.close()

cleanup_database()

# ==========================
# Root
# ==========================
@app.get("/")
def root():
    return {"msg": "Video API is running 🚀"}

# ==========================
# Upload video
# ==========================
@app.post("/upload")
async def upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.content_type.startswith("video/"):
        raise HTTPException(400, detail="File must be a video")
    try:
        unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
        file_path = os.path.join(TEMP_DIR, unique_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        cmd = [FFPROBE_PATH, "-v", "error", "-show_entries", "format=duration,size", "-of", "json", file_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        metadata = json.loads(result.stdout)["format"]
        duration = float(metadata.get("duration", 0))
        size = int(metadata.get("size", 0))

        db_video = crud.create_video(db, filename=unique_filename, duration=duration, size=size)
        return {"id": db_video.id, "filename": file.filename, "stored_filename": unique_filename, "duration": duration, "size": size}
    except Exception as e:
        raise HTTPException(500, detail=str(e))

# ==========================
# List videos
# ==========================
@app.get("/videos")
def list_videos(db: Session = Depends(get_db)):
    videos = crud.get_videos(db)
    return [
        {
            "id": video.id,
            "filename": video.filename,
            "original_filename": video.filename.split('_', 1)[1] if '_' in video.filename else video.filename,
            "duration": video.duration,
            "size": video.size,
            "upload_time": video.upload_time
        }
        for video in videos
    ]

# ==========================
# NEW: Video Quality Endpoints
# ==========================

@app.post("/videos/{video_id}/qualities/generate")
async def generate_video_qualities(
    video_id: int,
    request: QualityGenerationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Generate multiple quality versions of a video"""
    video = crud.get_video(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    input_path = os.path.join(TEMP_DIR, video.filename)
    if not os.path.exists(input_path):
        raise HTTPException(status_code=404, detail="Video file not found on server")
    
    # Check if qualities already exist
    existing_qualities = crud.get_available_qualities(db, video_id)
    new_qualities = [q for q in request.qualities if q not in existing_qualities]
    
    if not new_qualities:
        return {"message": "All requested qualities already exist", "existing_qualities": existing_qualities}
    
    # Start background processing
    background_tasks.add_task(process_video_qualities, video_id, video.filename, new_qualities, db)
    
    return {
        "message": f"Started generating {len(new_qualities)} quality versions",
        "video_id": video_id,
        "requested_qualities": new_qualities,
        "existing_qualities": existing_qualities
    }

@app.get("/videos/{video_id}/qualities")
def get_video_qualities(video_id: int, db: Session = Depends(get_db)):
    """Get all available quality versions for a video"""
    video = crud.get_video(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    qualities = crud.get_video_qualities(db, video_id)
    return {
        "video_id": video_id,
        "original_filename": video.filename,
        "available_qualities": [
            {
                "id": q.id,
                "quality": q.quality,
                "filename": q.filename,
                "bitrate": q.bitrate,
                "resolution": q.resolution,
                "filesize": q.filesize,
                "created_time": q.created_time
            }
            for q in qualities
        ]
    }

@app.get("/videos/{video_id}/qualities/{quality}")
def get_specific_quality(video_id: int, quality: str, db: Session = Depends(get_db)):
    """Get information about a specific quality version"""
    video = crud.get_video(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    quality_info = crud.get_video_by_quality(db, video_id, quality)
    if not quality_info:
        raise HTTPException(status_code=404, detail=f"Quality '{quality}' not found for this video")
    
    return {
        "id": quality_info.id,
        "video_id": video_id,
        "quality": quality_info.quality,
        "filename": quality_info.filename,
        "bitrate": quality_info.bitrate,
        "resolution": quality_info.resolution,
        "filesize": quality_info.filesize,
        "created_time": quality_info.created_time
    }

@app.get("/videos/{video_id}/download/{quality}")
def download_quality(video_id: int, quality: str, db: Session = Depends(get_db)):
    """Download a specific quality version of a video"""
    video = crud.get_video(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    quality_info = crud.get_video_by_quality(db, video_id, quality)
    if not quality_info:
        raise HTTPException(status_code=404, detail=f"Quality '{quality}' not found for this video")
    
    file_path = os.path.join(QUALITIES_DIR, quality_info.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Quality file not found on server")
    
    # Generate a user-friendly filename
    original_name = video.filename.split('_', 1)[1] if '_' in video.filename else video.filename
    download_name = f"{original_name.rsplit('.', 1)[0]}_{quality}.mp4"
    
    return FileResponse(
        path=file_path,
        filename=download_name,
        media_type="video/mp4"
    )

@app.get("/videos/{video_id}/stats")
def get_video_stats(video_id: int, db: Session = Depends(get_db)):
    """Get comprehensive statistics for a video"""
    stats = crud.get_video_stats(db, video_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return stats

@app.delete("/videos/{video_id}/qualities/{quality_id}")
def delete_video_quality(video_id: int, quality_id: int, db: Session = Depends(get_db)):
    """Delete a specific quality version"""
    quality_info = crud.get_quality_by_id(db, quality_id)
    if not quality_info or quality_info.video_id != video_id:
        raise HTTPException(status_code=404, detail="Quality not found")
    
    # Delete file from disk
    file_path = os.path.join(QUALITIES_DIR, quality_info.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Delete from database
    success = crud.delete_video_quality(db, quality_id)
    if success:
        return {"message": f"Quality '{quality_info.quality}' deleted successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete quality from database")

# ==========================
# Trim video
# ==========================
@app.post("/trim")
def trim_video(video_id: int, start_time: float, end_time: float, db: Session = Depends(get_db)):
    video = crud.get_video(db, video_id)
    if not video:
        raise HTTPException(404, detail="Video not found")

    input_path = os.path.join(TEMP_DIR, video.filename)
    if not os.path.exists(input_path):
        raise HTTPException(404, detail="Video file not found on server")

    out_filename = f"trimmed_{uuid.uuid4().hex}.mp4"
    out_path = os.path.join(PROCESSED_DIR, out_filename)

    cmd = [FFMPEG_PATH, "-i", input_path, "-ss", str(start_time), "-to", str(end_time), "-c", "copy", out_path]
    subprocess.run(cmd, capture_output=True, text=True)

    probe_cmd = [FFPROBE_PATH, "-v", "error", "-show_entries", "format=duration,size", "-of", "json", out_path]
    probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
    metadata = json.loads(probe_result.stdout)
    duration = float(metadata["format"]["duration"])
    size = int(metadata["format"]["size"])

    trimmed = crud.create_trimmed_video(db, video_id=video.id, filename=out_filename, start_time=start_time, end_time=end_time, duration=duration, size=size)
    return {"original_video_id": video.id, "trimmed_video_id": trimmed.id, "filename": out_filename, "duration": duration, "size": size}

# ==========================
# Download video
# ==========================
@app.get("/download/{filename}", response_class=FileResponse)
def download_file(filename: str):
    file_path = os.path.join(PROCESSED_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(404, detail="File not found")
    return FileResponse(path=file_path, filename=filename, media_type="video/mp4")

# ==========================
# FFmpeg helper functions
# ==========================
def add_text_overlay(input_video, output_video, text, font_path, x, y, start, end, fontsize=30, fontcolor="white"):
    cmd = [FFMPEG_PATH, "-i", input_video,
           "-vf", f"drawtext=text='{text}':fontfile='{font_path}':x={x}:y={y}:fontsize={fontsize}:fontcolor={fontcolor}:enable='between(t,{start},{end})'",
           "-codec:a", "copy", output_video]
    subprocess.run(cmd, check=True)

def add_image_overlay(input_video, output_video, image_path, x, y, start, end):
    cmd = [FFMPEG_PATH, "-i", input_video, "-i", image_path,
           "-filter_complex", f"overlay={x}:{y}:enable='between(t,{start},{end})'",
           "-codec:a", "copy", output_video]
    subprocess.run(cmd, check=True)

def add_video_overlay(input_video, output_video, overlay_video, x, y, start, end):
    cmd = [FFMPEG_PATH, "-i", input_video, "-i", overlay_video,
           "-filter_complex", f"[1:v]setpts=PTS-STARTPTS+{start}/TB[ov];[0:v][ov]overlay={x}:{y}:enable='between(t,{start},{end})'",
           "-codec:a", "copy", output_video]
    subprocess.run(cmd, check=True)

def add_watermark(input_video, output_video, watermark_path, x, y, opacity=0.5):
    cmd = [FFMPEG_PATH, "-i", input_video, "-i", watermark_path,
           "-filter_complex", f"[1]format=rgba,colorchannelmixer=aa={opacity}[wm];[0][wm]overlay={x}:{y}",
           "-codec:a", "copy", output_video]
    subprocess.run(cmd, check=True)

# ==========================
# Overlay / Watermark Endpoints
# ==========================

# Text Overlay
@app.post("/overlay/text")
async def overlay_text(
    video_id: int, text: str, language: str = "hi", x: int = 100, y: int = 50,
    start: float = 0, end: float = 5, fontsize: int = 30, fontcolor: str = "white",
    db: Session = Depends(get_db)
):
    video = crud.get_video(db, video_id)
    if not video:
        raise HTTPException(404, detail="Video not found")

    input_path = os.path.join(TEMP_DIR, video.filename)
    out_filename = f"overlay_text_{uuid.uuid4().hex}.mp4"
    output_path = os.path.join(PROCESSED_DIR, out_filename)

    font_map = {
        "en": r"assets/fonts/NotoSans-Regular.ttf",
        "hi": r"assets/fonts/NotoSansDevanagari-Regular.ttf",
        "ta": r"assets/fonts/NotoSansTamil-Regular.ttf",
        "te": r"assets/fonts/NotoSansTelugu-Regular.ttf"
    }
    font_path = font_map.get(language, r"assets/fonts/NotoSans-Regular.ttf")

    add_text_overlay(input_path, output_path, text, font_path, x, y, start, end, fontsize, fontcolor)

    overlay_op = crud.create_overlay(db, video.id, "text", out_filename)
    crud.create_text_overlay(
        db,
        overlay_op.id,
        text=text,
        font_path=font_path,
        fontsize=fontsize,
        fontcolor=fontcolor,
        language=language,
        x=x,
        y=y,
        start=start,
        end=end
    )
    return {"output_file": out_filename}

# Image Overlay
@app.post("/overlay/image")
async def overlay_image(
    video_id: int, image: UploadFile = File(...), x: int = 0, y: int = 0,
    start: float = 0, end: float = 5, db: Session = Depends(get_db)
):
    video = crud.get_video(db, video_id)
    if not video:
        raise HTTPException(404, detail="Video not found")

    input_path = os.path.join(TEMP_DIR, video.filename)
    out_filename = f"overlay_image_{uuid.uuid4().hex}.mp4"
    output_path = os.path.join(PROCESSED_DIR, out_filename)

    image_path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_{image.filename}")
    with open(image_path, "wb") as f:
        f.write(await image.read())

    add_image_overlay(input_path, output_path, image_path, x, y, start, end)

    overlay_op = crud.create_overlay(db, video.id, "image", out_filename)
    crud.create_image_overlay(
        db,
        overlay_op.id,
        image_path=image_path,
        x=x,
        y=y,
        start=start,
        end=end
    )
    return {"output_file": out_filename}

# Video Overlay
@app.post("/overlay/video")
async def overlay_video(
    video_id: int, overlay: UploadFile = File(...), x: int = 0, y: int = 0,
    start: float = 0, end: float = 5, db: Session = Depends(get_db)
):
    video = crud.get_video(db, video_id)
    if not video:
        raise HTTPException(404, detail="Video not found")

    input_path = os.path.join(TEMP_DIR, video.filename)
    out_filename = f"overlay_video_{uuid.uuid4().hex}.mp4"
    output_path = os.path.join(PROCESSED_DIR, out_filename)

    overlay_path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_{overlay.filename}")
    with open(overlay_path, "wb") as f:
        f.write(await overlay.read())

    add_video_overlay(input_path, output_path, overlay_path, x, y, start, end)

    overlay_op = crud.create_overlay(db, video.id, "video", out_filename)
    crud.create_video_overlay(
        db,
        overlay_op.id,
       overlay_video_path=overlay_path,
        x=x,
        y=y,
        start=start,
        end=end
    )
    return {"output_file": out_filename}

# Watermark
@app.post("/watermark/add")
async def add_watermark_api(
    video_id: int, watermark: UploadFile = File(...), x: int = 0, y: int = 0,
    opacity: float = 0.5, db: Session = Depends(get_db)
):
    video = crud.get_video(db, video_id)
    if not video:
        raise HTTPException(404, detail="Video not found")

    input_path = os.path.join(TEMP_DIR, video.filename)
    out_filename = f"watermarked_{uuid.uuid4().hex}.mp4"
    output_path = os.path.join(PROCESSED_DIR, out_filename)

    watermark_path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_{watermark.filename}")
    with open(watermark_path, "wb") as f:
        f.write(await watermark.read())

    add_watermark(input_path, output_path, watermark_path, x, y, opacity)

    overlay_op = crud.create_overlay(db, video.id, "watermark", out_filename)
    crud.create_watermark(
        db,
        overlay_op.id,
        watermark_path=watermark_path,
        x=x,
        y=y,
        opacity=opacity
    )

    #  Return response
    return {"output_file": out_filename, "overlay_id": overlay_op.id}