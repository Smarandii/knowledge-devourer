from pathlib import Path

# External tools
# Get from https://github.com/Smarandii/video_subtitler.git
VSUB_PYTHON = Path("E:/Projects/python/video subtitler/.venv/Scripts/python.exe")
VSUB_ENTRYPOINT = Path("E:/Projects/python/video subtitler/main.py")

# Directory structure
BASE_DIR = Path(__file__).parent.parent
REELS_DIR = BASE_DIR / "reels"
PREVIEWS_DIR = BASE_DIR / "reels_previews"
DESCRIPTIONS_DIR = BASE_DIR / "reels_descriptions"
AUDIO_DIR = BASE_DIR / "reels_audio"
VSUB_OUTPUT_DIR = BASE_DIR / "vsub_output"
POSTS_DIR = BASE_DIR / "posts"

# Rate limiting
MIN_DELAY = 5
MAX_DELAY = 20
