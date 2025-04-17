import os
import requests
import subprocess

from pathlib import Path
from config import (
    VSUB_PYTHON, VSUB_ENTRYPOINT, VSUB_OUTPUT_DIR,
)

from instagram_client import init_reels_client
from logger import setup_logging

logger = setup_logging()


async def download_reels(clip_path: str, reel_id: str):
    logger.info("Starting download for reel id: %s", reel_id)
    client = await init_reels_client()

    logger.info("Fetching reel data…")
    info = await client.get(reel_id)
    logger.debug("Reel info received: %s", info)

    if not info.videos or not info.videos[0].url:
        logger.error("No video URL found in reel data; skipping.")
        return info

    video_url = info.videos[0].url
    logger.info("Downloading video from %s", video_url)
    resp = requests.get(video_url, stream=True)
    resp.raise_for_status()

    os.makedirs(os.path.dirname(clip_path), exist_ok=True)
    total = 0
    with open(clip_path, "wb") as f:
        for chunk in resp.iter_content(8192):
            f.write(chunk)
            total += len(chunk)
    logger.info("Saved video to %s (%d bytes)", clip_path, total)

    return info


def download_preview_image(url: str, dest: Path):
    logger.info("Downloading preview image from %s", url)
    resp = requests.get(url, stream=True)
    resp.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(8192):
            f.write(chunk)


def run_vsub(video: Path, srt: Path, txt: Path):
    VSUB_OUTPUT_DIR.mkdir(exist_ok=True)
    cmd = [
        str(VSUB_PYTHON), str(VSUB_ENTRYPOINT),
        str(video), "-s", str(srt), "-t", str(txt), "-o", str(VSUB_OUTPUT_DIR)
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    logger.info("vsub stdout:\n%s", proc.stdout)
    if proc.stderr:
        logger.error("vsub stderr:\n%s", proc.stderr)
