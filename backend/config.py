import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
RAW_DIR = UPLOAD_DIR / "raw"
PROCESSED_DIR = UPLOAD_DIR / "processed"
OUTPUT_DIR = BASE_DIR / "outputs"

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
