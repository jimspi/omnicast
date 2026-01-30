import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Detect if running on Vercel (serverless)
IS_VERCEL = os.environ.get('VERCEL', False)

BASE_DIR = Path(__file__).resolve().parent.parent

# Use /tmp for Vercel serverless, local directories otherwise
if IS_VERCEL:
    UPLOAD_DIR = Path("/tmp/uploads")
    OUTPUT_DIR = Path("/tmp/outputs")
else:
    UPLOAD_DIR = BASE_DIR / "uploads"
    OUTPUT_DIR = BASE_DIR / "outputs"

RAW_DIR = UPLOAD_DIR / "raw"
PROCESSED_DIR = UPLOAD_DIR / "processed"

# Static files directory
STATIC_DIR = BASE_DIR / "frontend" / "static"
TEMPLATES_DIR = BASE_DIR / "frontend" / "templates"

# Ensure directories exist
for dir_path in [RAW_DIR, PROCESSED_DIR, OUTPUT_DIR / "tv", OUTPUT_DIR / "web",
                 OUTPUT_DIR / "social", OUTPUT_DIR / "youtube", OUTPUT_DIR / "podcast"]:
    dir_path.mkdir(parents=True, exist_ok=True)

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# File size limits
MAX_VIDEO_SIZE_MB = 500
MAX_AUDIO_SIZE_MB = 100
MAX_TEXT_SIZE_MB = 10

# Supported formats
SUPPORTED_VIDEO_FORMATS = [".mp4", ".mov", ".avi", ".mkv", ".webm"]
SUPPORTED_AUDIO_FORMATS = [".mp3", ".wav", ".m4a", ".aac", ".ogg"]
SUPPORTED_TEXT_FORMATS = [".txt", ".md", ".doc", ".docx"]
