import os
import subprocess
import asyncio
import json
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFont
import numpy as np

from .config import PROCESSED_DIR, OUTPUT_DIR


async def extract_audio_from_video(video_path: str, output_path: Optional[str] = None) -> str:
    """Extract audio track from video file using FFmpeg."""
    if output_path is None:
        video_name = Path(video_path).stem
        output_path = str(PROCESSED_DIR / f"{video_name}_audio.mp3")

    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "libmp3lame", "-q:a", "2",
        output_path
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await process.communicate()

    return output_path


async def get_video_info(video_path: str) -> Dict[str, Any]:
    """Get video metadata using FFprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        video_path
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await process.communicate()

    return json.loads(stdout.decode())


async def create_social_media_video(
    source_video: str,
    output_path: str,
    headline: str,
    subtitles: List[Dict],
    hook_text: str,
    text_overlays: List[Dict],
    duration: int = 45
) -> str:
    """Create a social media optimized video with overlays and subtitles."""

    # Get video info
    info = await get_video_info(source_video)
    video_stream = next((s for s in info.get('streams', []) if s.get('codec_type') == 'video'), {})

    original_width = int(video_stream.get('width', 1920))
    original_height = int(video_stream.get('height', 1080))

    # Target 9:16 aspect ratio for social media
    target_width = 1080
    target_height = 1920

    # Generate SRT file for subtitles
    srt_path = str(PROCESSED_DIR / "temp_subtitles.srt")
    await generate_srt_file(subtitles, srt_path)

    # Create text overlay filter
    overlay_filters = create_text_overlay_filters(headline, hook_text, text_overlays, target_width, target_height)

    # Build FFmpeg command
    filter_complex = f"""
[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=increase,
crop={target_width}:{target_height},
setsar=1,
{overlay_filters}
subtitles={srt_path}:force_style='FontSize=24,FontName=Arial Bold,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline=2,Alignment=2'
[outv]
"""

    filter_complex = filter_complex.replace('\n', '')

    cmd = [
        "ffmpeg", "-y",
        "-i", source_video,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(duration),
        "-movflags", "+faststart",
        output_path
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        # Fallback to simpler processing if complex filter fails
        return await create_social_video_simple(source_video, output_path, headline, subtitles, duration)

    return output_path


async def create_social_video_simple(
    source_video: str,
    output_path: str,
    headline: str,
    subtitles: List[Dict],
    duration: int = 45
) -> str:
    """Simplified social media video creation."""
    srt_path = str(PROCESSED_DIR / "temp_subtitles.srt")
    await generate_srt_file(subtitles, srt_path)

    # Escape special characters in headline
    safe_headline = headline.replace("'", "'\\''").replace(":", "\\:")

    filter_complex = f"""
scale=1080:1920:force_original_aspect_ratio=increase,
crop=1080:1920,
drawtext=text='{safe_headline}':fontsize=48:fontcolor=white:borderw=3:bordercolor=black:x=(w-text_w)/2:y=100:font=Arial,
subtitles={srt_path}:force_style='FontSize=28,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline=2'
"""

    filter_complex = filter_complex.replace('\n', '')

    cmd = [
        "ffmpeg", "-y",
        "-i", source_video,
        "-vf", filter_complex,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(duration),
        "-movflags", "+faststart",
        output_path
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await process.communicate()

    return output_path


async def generate_srt_file(subtitles: List[Dict], output_path: str) -> str:
    """Generate SRT subtitle file."""
    srt_content = ""
    for i, segment in enumerate(subtitles, 1):
        start = format_srt_time(segment.get('start', i * 3 - 3))
        end = format_srt_time(segment.get('end', i * 3))
        text = segment.get('text', '')
        srt_content += f"{i}\n{start} --> {end}\n{text}\n\n"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(srt_content)

    return output_path


def format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT time format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def create_text_overlay_filters(
    headline: str,
    hook_text: str,
    text_overlays: List[Dict],
    width: int,
    height: int
) -> str:
    """Create FFmpeg drawtext filters for text overlays."""
    filters = []

    # Escape text for FFmpeg
    safe_headline = headline.replace("'", "'\\''").replace(":", "\\:")
    safe_hook = hook_text.replace("'", "'\\''").replace(":", "\\:")

    # Headline at top
    filters.append(
        f"drawtext=text='{safe_headline}':fontsize=52:fontcolor=white:borderw=4:bordercolor=black:"
        f"x=(w-text_w)/2:y=120:font=Arial"
    )

    # Hook text (shown in first 3 seconds)
    filters.append(
        f"drawtext=text='{safe_hook}':fontsize=36:fontcolor=yellow:borderw=3:bordercolor=black:"
        f"x=(w-text_w)/2:y=h-200:font=Arial:enable='lt(t,3)'"
    )

    # Additional text overlays
    for overlay in text_overlays:
        time = overlay.get('time', 0)
        text = overlay.get('text', '').replace("'", "'\\''").replace(":", "\\:")
        style = overlay.get('style', 'default')

        if style == 'headline':
            fontsize = 48
            color = 'white'
            y_pos = 180
        elif style == 'fact':
            fontsize = 40
            color = 'yellow'
            y_pos = height - 300
        else:
            fontsize = 36
            color = 'white'
            y_pos = height // 2

        filters.append(
            f"drawtext=text='{text}':fontsize={fontsize}:fontcolor={color}:borderw=3:bordercolor=black:"
            f"x=(w-text_w)/2:y={y_pos}:font=Arial:enable='between(t,{time},{time+5})'"
        )

    return ','.join(filters)


async def create_youtube_video(
    source_video: str,
    output_path: str,
    title: str,
    intro_text: str,
    outro_text: str,
    timestamps: List[Dict]
) -> str:
    """Create YouTube-optimized video with intro/outro cards."""

    # YouTube uses 16:9 aspect ratio
    target_width = 1920
    target_height = 1080

    safe_title = title.replace("'", "'\\''").replace(":", "\\:")
    safe_outro = outro_text.replace("'", "'\\''").replace(":", "\\:")

    # Add title card at beginning and end card
    filter_complex = f"""
scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,
pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:black,
drawtext=text='{safe_title}':fontsize=64:fontcolor=white:borderw=4:bordercolor=black:x=(w-text_w)/2:y=(h-text_h)/2:font=Arial:enable='lt(t,4)',
drawtext=text='Subscribe for more':fontsize=48:fontcolor=red:borderw=3:bordercolor=white:x=(w-text_w)/2:y=h-100:font=Arial:enable='gt(t,duration-10)'
"""

    filter_complex = filter_complex.replace('\n', '')

    cmd = [
        "ffmpeg", "-y",
        "-i", source_video,
        "-vf", filter_complex,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        output_path
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await process.communicate()

    return output_path


async def create_podcast_audio(
    narration_audio: str,
    interview_audio: Optional[str],
    output_path: str,
    intro_music_path: Optional[str] = None,
    outro_music_path: Optional[str] = None
) -> str:
    """Create podcast audio with music and mixed interviews."""

    if interview_audio and os.path.exists(interview_audio):
        # Mix narration with interview audio
        # This creates a simple concatenation - in production you'd want crossfades
        cmd = [
            "ffmpeg", "-y",
            "-i", narration_audio,
            "-i", interview_audio,
            "-filter_complex",
            "[0:a][1:a]concat=n=2:v=0:a=1[outa]",
            "-map", "[outa]",
            "-c:a", "libmp3lame", "-q:a", "2",
            output_path
        ]
    else:
        # Just use narration audio
        cmd = [
            "ffmpeg", "-y",
            "-i", narration_audio,
            "-c:a", "libmp3lame", "-q:a", "2",
            output_path
        ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await process.communicate()

    return output_path


async def extract_keyframes(video_path: str, output_dir: str, num_frames: int = 10) -> List[str]:
    """Extract keyframes from video for thumbnail generation."""
    output_pattern = os.path.join(output_dir, "keyframe_%03d.jpg")

    # Get video duration first
    info = await get_video_info(video_path)
    duration = float(info.get('format', {}).get('duration', 60))

    # Calculate frame interval
    interval = duration / num_frames

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"fps=1/{interval}",
        "-frames:v", str(num_frames),
        "-q:v", "2",
        output_pattern
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await process.communicate()

    # Return list of generated frame paths
    frames = sorted([
        os.path.join(output_dir, f)
        for f in os.listdir(output_dir)
        if f.startswith("keyframe_") and f.endswith(".jpg")
    ])

    return frames


async def create_thumbnail(
    base_image_path: str,
    output_path: str,
    title: str,
    style: str = "youtube"
) -> str:
    """Create a thumbnail image with text overlay."""
    try:
        img = Image.open(base_image_path)

        if style == "youtube":
            # Resize to YouTube thumbnail size
            img = img.resize((1280, 720), Image.Resampling.LANCZOS)
        elif style == "social":
            # Resize for social media
            img = img.resize((1080, 1080), Image.Resampling.LANCZOS)

        draw = ImageDraw.Draw(img)

        # Try to use a bold font, fallback to default
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
        except:
            font = ImageFont.load_default()

        # Add text with outline
        text = title[:50] + "..." if len(title) > 50 else title

        # Get text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (img.width - text_width) // 2
        y = img.height - text_height - 50

        # Draw outline
        outline_color = "black"
        for dx in [-3, -2, -1, 0, 1, 2, 3]:
            for dy in [-3, -2, -1, 0, 1, 2, 3]:
                draw.text((x + dx, y + dy), text, font=font, fill=outline_color)

        # Draw main text
        draw.text((x, y), text, font=font, fill="white")

        img.save(output_path, "JPEG", quality=95)
        return output_path

    except Exception as e:
        print(f"Thumbnail creation error: {e}")
        return base_image_path


async def trim_video(video_path: str, output_path: str, start: float, end: float) -> str:
    """Trim video to specified start and end times."""
    duration = end - start

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", video_path,
        "-t", str(duration),
        "-c", "copy",
        output_path
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await process.communicate()

    return output_path


async def normalize_audio(audio_path: str, output_path: str, target_lufs: float = -16.0) -> str:
    """Normalize audio levels using EBU R128."""
    cmd = [
        "ffmpeg", "-y",
        "-i", audio_path,
        "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11",
        "-c:a", "libmp3lame", "-q:a", "2",
        output_path
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await process.communicate()

    return output_path
