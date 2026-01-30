import os
import uuid
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import aiofiles

from .config import (
    BASE_DIR, RAW_DIR, PROCESSED_DIR, OUTPUT_DIR,
    SUPPORTED_VIDEO_FORMATS, SUPPORTED_AUDIO_FORMATS, SUPPORTED_TEXT_FORMATS,
    OPENAI_API_KEY, IS_VERCEL, STATIC_DIR, TEMPLATES_DIR
)
from . import openai_service
from . import media_processor

app = FastAPI(
    title="OmniCast - Multi-Format News Distribution Platform",
    description="Transform story materials into TV, Web, Social Media, YouTube, and Podcast content",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
if OUTPUT_DIR.exists():
    app.mount("/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# In-memory job storage (in production, use Redis or a database)
jobs: Dict[str, Dict[str, Any]] = {}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main application page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "openai_configured": bool(OPENAI_API_KEY),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    file_type: str = Form(...)
):
    """Upload a file (video, audio, or text)."""
    # Validate file extension
    ext = Path(file.filename).suffix.lower()

    if file_type == "video" and ext not in SUPPORTED_VIDEO_FORMATS:
        raise HTTPException(400, f"Unsupported video format. Supported: {SUPPORTED_VIDEO_FORMATS}")
    elif file_type == "audio" and ext not in SUPPORTED_AUDIO_FORMATS:
        raise HTTPException(400, f"Unsupported audio format. Supported: {SUPPORTED_AUDIO_FORMATS}")
    elif file_type == "text" and ext not in SUPPORTED_TEXT_FORMATS:
        raise HTTPException(400, f"Unsupported text format. Supported: {SUPPORTED_TEXT_FORMATS}")

    # Generate unique filename
    file_id = str(uuid.uuid4())
    filename = f"{file_id}{ext}"
    file_path = RAW_DIR / filename

    # Save file
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)

    return {
        "file_id": file_id,
        "filename": filename,
        "file_type": file_type,
        "path": str(file_path),
        "size": len(content)
    }


@app.post("/api/process")
async def process_story(
    background_tasks: BackgroundTasks,
    notes: str = Form(default=""),
    interview_video_id: Optional[str] = Form(default=None),
    broll_video_id: Optional[str] = Form(default=None),
    output_formats: str = Form(default="tv,web,social,youtube,podcast")
):
    """Process story materials and generate multi-format content."""
    job_id = str(uuid.uuid4())

    # Parse requested formats
    formats = [f.strip().lower() for f in output_formats.split(",")]

    # Initialize job
    jobs[job_id] = {
        "id": job_id,
        "status": "processing",
        "progress": 0,
        "formats": formats,
        "outputs": {},
        "errors": [],
        "created_at": datetime.now().isoformat()
    }

    # Start background processing
    background_tasks.add_task(
        process_story_background,
        job_id, notes, interview_video_id, broll_video_id, formats
    )

    return {"job_id": job_id, "status": "processing"}


async def process_story_background(
    job_id: str,
    notes: str,
    interview_video_id: Optional[str],
    broll_video_id: Optional[str],
    formats: List[str]
):
    """Background task to process story and generate all formats."""
    try:
        job = jobs[job_id]
        total_steps = len(formats) + 2  # +2 for transcription and analysis
        current_step = 0

        # Step 1: Transcribe interview video if provided
        interview_transcript = ""
        interview_audio_path = None

        if interview_video_id:
            job["status"] = "Transcribing interview..."
            # Find the video file
            interview_video = find_uploaded_file(interview_video_id)
            if interview_video:
                # Extract audio
                interview_audio_path = str(PROCESSED_DIR / f"{interview_video_id}_audio.mp3")
                await media_processor.extract_audio_from_video(interview_video, interview_audio_path)

                # Transcribe
                interview_transcript = await openai_service.transcribe_audio_simple(interview_audio_path)

        current_step += 1
        job["progress"] = int((current_step / total_steps) * 100)

        # Step 2: Analyze B-roll if provided
        broll_description = ""
        broll_video_path = None

        if broll_video_id:
            job["status"] = "Analyzing B-roll footage..."
            broll_video_path = find_uploaded_file(broll_video_id)
            if broll_video_path:
                # Get video info for description
                video_info = await media_processor.get_video_info(broll_video_path)
                duration = video_info.get('format', {}).get('duration', 'unknown')
                broll_description = f"B-roll footage available, duration: {duration} seconds"

        current_step += 1
        job["progress"] = int((current_step / total_steps) * 100)

        # Build story context
        story_context = {
            "notes": notes,
            "interview_transcript": interview_transcript,
            "broll_description": broll_description
        }

        # Generate each format
        for format_type in formats:
            try:
                job["status"] = f"Generating {format_type.upper()} content..."

                if format_type == "tv":
                    result = await generate_tv_output(job_id, story_context)
                    job["outputs"]["tv"] = result

                elif format_type == "web":
                    result = await generate_web_output(job_id, story_context)
                    job["outputs"]["web"] = result

                elif format_type == "social":
                    result = await generate_social_output(
                        job_id, story_context, broll_video_path or interview_video_path_from_id(interview_video_id)
                    )
                    job["outputs"]["social"] = result

                elif format_type == "youtube":
                    result = await generate_youtube_output(
                        job_id, story_context, broll_video_path or interview_video_path_from_id(interview_video_id)
                    )
                    job["outputs"]["youtube"] = result

                elif format_type == "podcast":
                    result = await generate_podcast_output(job_id, story_context, interview_audio_path)
                    job["outputs"]["podcast"] = result

                current_step += 1
                job["progress"] = int((current_step / total_steps) * 100)

            except Exception as e:
                job["errors"].append(f"Error generating {format_type}: {str(e)}")

        job["status"] = "completed"
        job["progress"] = 100
        job["completed_at"] = datetime.now().isoformat()

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["errors"].append(str(e))


def find_uploaded_file(file_id: str) -> Optional[str]:
    """Find uploaded file by ID."""
    for ext in SUPPORTED_VIDEO_FORMATS + SUPPORTED_AUDIO_FORMATS:
        path = RAW_DIR / f"{file_id}{ext}"
        if path.exists():
            return str(path)
    return None


def interview_video_path_from_id(video_id: Optional[str]) -> Optional[str]:
    """Get video path from ID."""
    if not video_id:
        return None
    return find_uploaded_file(video_id)


async def generate_tv_output(job_id: str, story_context: Dict) -> Dict:
    """Generate TV broadcast content."""
    # Generate TV script using OpenAI
    tv_content = await openai_service.generate_tv_script(story_context)

    # Save the script
    output_path = OUTPUT_DIR / "tv" / f"{job_id}_tv_script.json"
    async with aiofiles.open(output_path, 'w') as f:
        await f.write(json.dumps(tv_content, indent=2))

    # Also save as formatted text
    text_path = OUTPUT_DIR / "tv" / f"{job_id}_tv_script.txt"
    async with aiofiles.open(text_path, 'w') as f:
        await f.write(tv_content.get("full_script", ""))

    return {
        "type": "tv",
        "script": tv_content,
        "files": {
            "json": f"/outputs/tv/{job_id}_tv_script.json",
            "text": f"/outputs/tv/{job_id}_tv_script.txt"
        }
    }


async def generate_web_output(job_id: str, story_context: Dict) -> Dict:
    """Generate web article content."""
    # Generate web article using OpenAI
    web_content = await openai_service.generate_web_article(story_context)

    # Save as JSON
    json_path = OUTPUT_DIR / "web" / f"{job_id}_article.json"
    async with aiofiles.open(json_path, 'w') as f:
        await f.write(json.dumps(web_content, indent=2))

    # Save as HTML file
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{web_content.get('meta_description', '')}">
    <title>{web_content.get('headline', 'Article')}</title>
    <style>
        body {{ font-family: Georgia, serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.8; }}
        h1 {{ font-size: 2.5em; margin-bottom: 0.5em; }}
        .meta {{ color: #666; margin-bottom: 2em; }}
        .lead {{ font-size: 1.3em; font-weight: 500; margin-bottom: 1.5em; }}
        blockquote {{ border-left: 4px solid #007bff; padding-left: 20px; margin: 20px 0; font-style: italic; }}
        .tags {{ margin-top: 30px; }}
        .tag {{ background: #f0f0f0; padding: 5px 10px; border-radius: 3px; margin-right: 5px; font-size: 0.9em; }}
    </style>
</head>
<body>
    <article>
        <h1>{web_content.get('headline', '')}</h1>
        <div class="meta">Generated by OmniCast</div>
        <div class="lead">{web_content.get('lead', '')}</div>
        <div class="content">
            {web_content.get('body_html', web_content.get('full_article_html', ''))}
        </div>
        <div class="tags">
            {''.join([f'<span class="tag">{tag}</span>' for tag in web_content.get('tags', [])])}
        </div>
    </article>
</body>
</html>"""

    html_path = OUTPUT_DIR / "web" / f"{job_id}_article.html"
    async with aiofiles.open(html_path, 'w') as f:
        await f.write(html_content)

    return {
        "type": "web",
        "content": web_content,
        "files": {
            "json": f"/outputs/web/{job_id}_article.json",
            "html": f"/outputs/web/{job_id}_article.html"
        }
    }


async def generate_social_output(job_id: str, story_context: Dict, video_path: Optional[str]) -> Dict:
    """Generate social media content with video."""
    # Generate social media content using OpenAI
    social_content = await openai_service.generate_social_media_content(story_context)

    # Save content as JSON
    json_path = OUTPUT_DIR / "social" / f"{job_id}_social.json"
    async with aiofiles.open(json_path, 'w') as f:
        await f.write(json.dumps(social_content, indent=2))

    result = {
        "type": "social",
        "content": social_content,
        "files": {
            "json": f"/outputs/social/{job_id}_social.json"
        }
    }

    # If video is provided, create social media video
    if video_path and os.path.exists(video_path):
        try:
            output_video = str(OUTPUT_DIR / "social" / f"{job_id}_social_video.mp4")

            await media_processor.create_social_media_video(
                source_video=video_path,
                output_path=output_video,
                headline=social_content.get("headline_overlay", "Breaking News"),
                subtitles=social_content.get("subtitle_segments", []),
                hook_text=social_content.get("hook_text", ""),
                text_overlays=social_content.get("text_overlays", []),
                duration=social_content.get("suggested_duration", 45)
            )

            result["files"]["video"] = f"/outputs/social/{job_id}_social_video.mp4"
        except Exception as e:
            result["video_error"] = str(e)

    # Generate SRT subtitle file
    srt_content = await openai_service.generate_subtitle_srt(
        social_content.get("subtitle_segments", [])
    )
    srt_path = OUTPUT_DIR / "social" / f"{job_id}_subtitles.srt"
    async with aiofiles.open(srt_path, 'w') as f:
        await f.write(srt_content)
    result["files"]["subtitles"] = f"/outputs/social/{job_id}_subtitles.srt"

    return result


async def generate_youtube_output(job_id: str, story_context: Dict, video_path: Optional[str]) -> Dict:
    """Generate YouTube content."""
    # Generate YouTube content using OpenAI
    youtube_content = await openai_service.generate_youtube_content(story_context)

    # Save content as JSON
    json_path = OUTPUT_DIR / "youtube" / f"{job_id}_youtube.json"
    async with aiofiles.open(json_path, 'w') as f:
        await f.write(json.dumps(youtube_content, indent=2))

    # Save description file (ready to paste into YouTube)
    desc_content = f"""{youtube_content.get('title', '')}

{youtube_content.get('description', '')}

TIMESTAMPS:
{chr(10).join([f"{t.get('time', '')} - {t.get('label', '')}" for t in youtube_content.get('timestamps', [])])}

TAGS: {', '.join(youtube_content.get('tags', []))}
"""

    desc_path = OUTPUT_DIR / "youtube" / f"{job_id}_youtube_description.txt"
    async with aiofiles.open(desc_path, 'w') as f:
        await f.write(desc_content)

    # Save full script
    script_path = OUTPUT_DIR / "youtube" / f"{job_id}_youtube_script.txt"
    async with aiofiles.open(script_path, 'w') as f:
        await f.write(youtube_content.get('full_script', ''))

    result = {
        "type": "youtube",
        "content": youtube_content,
        "files": {
            "json": f"/outputs/youtube/{job_id}_youtube.json",
            "description": f"/outputs/youtube/{job_id}_youtube_description.txt",
            "script": f"/outputs/youtube/{job_id}_youtube_script.txt"
        }
    }

    # If video is provided, create YouTube-optimized video
    if video_path and os.path.exists(video_path):
        try:
            output_video = str(OUTPUT_DIR / "youtube" / f"{job_id}_youtube_video.mp4")

            await media_processor.create_youtube_video(
                source_video=video_path,
                output_path=output_video,
                title=youtube_content.get("title", ""),
                intro_text=youtube_content.get("script", {}).get("intro", ""),
                outro_text=youtube_content.get("end_screen", {}).get("subscribe_cta", ""),
                timestamps=youtube_content.get("timestamps", [])
            )

            result["files"]["video"] = f"/outputs/youtube/{job_id}_youtube_video.mp4"

            # Generate thumbnail
            keyframes_dir = str(PROCESSED_DIR / f"{job_id}_keyframes")
            os.makedirs(keyframes_dir, exist_ok=True)
            keyframes = await media_processor.extract_keyframes(video_path, keyframes_dir, 5)

            if keyframes:
                thumbnail_path = str(OUTPUT_DIR / "youtube" / f"{job_id}_thumbnail.jpg")
                await media_processor.create_thumbnail(
                    keyframes[0],
                    thumbnail_path,
                    youtube_content.get("title", "")[:30]
                )
                result["files"]["thumbnail"] = f"/outputs/youtube/{job_id}_thumbnail.jpg"

        except Exception as e:
            result["video_error"] = str(e)

    return result


async def generate_podcast_output(job_id: str, story_context: Dict, interview_audio: Optional[str]) -> Dict:
    """Generate podcast content with audio."""
    # Generate podcast content using OpenAI
    podcast_content = await openai_service.generate_podcast_content(story_context)

    # Save content as JSON
    json_path = OUTPUT_DIR / "podcast" / f"{job_id}_podcast.json"
    async with aiofiles.open(json_path, 'w') as f:
        await f.write(json.dumps(podcast_content, indent=2))

    # Save show notes
    notes_path = OUTPUT_DIR / "podcast" / f"{job_id}_show_notes.txt"
    async with aiofiles.open(notes_path, 'w') as f:
        await f.write(f"Episode: {podcast_content.get('episode_title', '')}\n\n")
        await f.write(f"Description: {podcast_content.get('episode_description', '')}\n\n")
        await f.write(f"Show Notes:\n{podcast_content.get('show_notes', '')}")

    # Save transcript
    transcript_path = OUTPUT_DIR / "podcast" / f"{job_id}_transcript.txt"
    async with aiofiles.open(transcript_path, 'w') as f:
        await f.write(podcast_content.get('transcript', podcast_content.get('full_script', '')))

    result = {
        "type": "podcast",
        "content": podcast_content,
        "files": {
            "json": f"/outputs/podcast/{job_id}_podcast.json",
            "show_notes": f"/outputs/podcast/{job_id}_show_notes.txt",
            "transcript": f"/outputs/podcast/{job_id}_transcript.txt"
        }
    }

    # Generate TTS narration audio
    try:
        narration_script = podcast_content.get('full_script', '')
        if narration_script:
            narration_path = str(OUTPUT_DIR / "podcast" / f"{job_id}_narration.mp3")
            await openai_service.generate_text_to_speech(
                narration_script[:4096],  # TTS has limits
                narration_path,
                voice="onyx"  # Professional voice for news
            )

            # Create final podcast audio
            final_audio_path = str(OUTPUT_DIR / "podcast" / f"{job_id}_podcast.mp3")
            await media_processor.create_podcast_audio(
                narration_audio=narration_path,
                interview_audio=interview_audio,
                output_path=final_audio_path
            )

            result["files"]["audio"] = f"/outputs/podcast/{job_id}_podcast.mp3"

    except Exception as e:
        result["audio_error"] = str(e)

    return result


@app.get("/api/job/{job_id}")
async def get_job_status(job_id: str):
    """Get the status of a processing job."""
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")

    return jobs[job_id]


@app.get("/api/jobs")
async def list_jobs():
    """List all jobs."""
    return {"jobs": list(jobs.values())}


@app.delete("/api/job/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its outputs."""
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")

    # Clean up files
    job = jobs[job_id]
    for format_type, output in job.get("outputs", {}).items():
        for file_key, file_path in output.get("files", {}).items():
            full_path = BASE_DIR / file_path.lstrip("/")
            if full_path.exists():
                os.remove(full_path)

    del jobs[job_id]
    return {"status": "deleted"}


@app.get("/api/download/{format_type}/{filename}")
async def download_file(format_type: str, filename: str):
    """Download a generated file."""
    file_path = OUTPUT_DIR / format_type / filename

    if not file_path.exists():
        raise HTTPException(404, "File not found")

    return FileResponse(file_path, filename=filename)


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "type": type(exc).__name__}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
