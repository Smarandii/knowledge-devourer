from pathlib import Path

# Directory structure
BASE_DIR = Path(__file__).parent.parent
REELS_DIR = BASE_DIR / "reels"
PREVIEWS_DIR = BASE_DIR / "reels_previews"
DESCRIPTIONS_DIR = BASE_DIR / "reels_descriptions"
AUDIO_DIR = BASE_DIR / "reels_audio"
SUBWHISPERER_OUTPUT_DIR = BASE_DIR / "subwhisperer_output"
POSTS_DIR = BASE_DIR / "posts"

# Rate limiting
MIN_DELAY = 5
MAX_DELAY = 20


# TODO: CHECK WHY PREVIEWS ARE FAILING TO DOWNLOAD
