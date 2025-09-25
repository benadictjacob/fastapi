Backend Engineer Assignment – Video Processing APIs
🎥 Project Overview

This project implements a FastAPI backend for a video editing platform. It supports video upload, trimming, overlays, watermarking, multiple output qualities, and asynchronous processing with a Postgres database for metadata storage.

🔹 Features

Video Upload & Metadata

Upload video files via API.

Metadata stored in Postgres: filename, size, duration, upload_time.

List all uploaded videos.

Video Trimming

POST /trim endpoint: provide video ID + start/end timestamps.

Returns trimmed video.

Stores trimmed video info in DB linked to original video.

Overlays & Watermarking

Add text, image, or video overlays with position and timing.

Support for texts in different Indian languages.

Add watermarks (image/logo).

Overlay/watermark configurations saved in DB.

Async Processing

Video processing happens asynchronously using Celery + Redis (or FastAPI background tasks).

Endpoints:

GET /status/{job_id} → check job status.

GET /result/{job_id} → download processed video.

Returns job_id immediately for long-running tasks.

Multiple Output Qualities

Generate videos in 1080p, 720p, and 480p.

All versions saved in DB.

API to download specific quality.

🔹 Project Structure
/backend
├── app/
│   ├── main.py
│   ├── routes/
│   ├── services/
│   ├── models.py
│   └── database.py
├── migrations/
├── requirements.txt
├── celery_worker.py
└── README.md

🔹 Setup & Installation

Clone the repo (or extract ZIP)

git clone <repo-link>
cd backend


Create & activate virtual environment

python -m venv venv
source venv/bin/activate      # Linux / Mac
venv\Scripts\activate         # Windows


Install dependencies

pip install -r requirements.txt


Setup Postgres database

CREATE DATABASE video_db;


Update .env with DB credentials:

DATABASE_URL=postgresql://user:password@localhost:5432/video_db


Run migrations

alembic upgrade head


Start FastAPI server

uvicorn app.main:app --reload


Start Celery worker (if using Celery)

celery -A celery_worker.celery_app worker --loglevel=info

🔹 API Endpoints
Endpoint	Method	Description
/upload	POST	Upload video
/videos	GET	List uploaded videos
/trim	POST	Trim video by start/end timestamps
/overlay	POST	Add text/image/video overlay
/watermark	POST	Add watermark to video
/status/{job_id}	GET	Check job status
/result/{job_id}	GET	Download processed video
/quality/{video_id}?res=720p	GET	Download specific resolution

OpenAPI docs available at: http://localhost:8000/docs

🔹 Demo Video

You can watch the demo here: YouTube Link

🔹 Notes

All video processing uses ffmpeg commands integrated in services.

Async jobs ensure API requests are non-blocking.

Supports multiple languages for text overlays.

Proper DB schema for videos, trims, overlays, watermarks, and job tracking.

Optional: Docker setup available for containerized deployment.

🔹 Author

[Benadict Jacob]
Email: [benadictjacob9@gmail.com]
