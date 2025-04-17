import asyncio
import os
import random
import subprocess
import time
import json
from pathlib import Path

from .config import (
    DESCRIPTIONS_DIR, POSTS_DIR, REELS_DIR, PREVIEWS_DIR, AUDIO_DIR,
    MIN_DELAY, MAX_DELAY, VSUB_PYTHON, VSUB_ENTRYPOINT
)
from .instagram_client import get_instagram_client
from .utils import to_dict_recursively, extract_reel_id_from_link
from .downloader import download_reels, download_preview_image, run_vsub
from .logger import setup_logging

logger = setup_logging()


def process_posts(links: list[str]):
    ig = get_instagram_client()
    for idx, link in enumerate(links, 1):
        ctype, code = extract_reel_id_from_link(link)
        if ctype != "post":
            continue
        desc_path = DESCRIPTIONS_DIR / f"{code}.json"
        if desc_path.exists():
            logger.info("Skipping post %s; already downloaded.", code)
            continue

        post = ig.post(code)
        desc_path.parent.mkdir(exist_ok=True)
        with open(desc_path, "w", encoding="utf-8") as fh:
            json_data = to_dict_recursively(post)
            fh.write(json.dumps(json_data, indent=2, ensure_ascii=False))

        for i, media in enumerate(ig.download(post, parallel=4), 1):
            ext = media.content_type.split("/")[-1].lower()
            filename = POSTS_DIR / f"{code}_{i:03d}.{ext}"
            filename.parent.mkdir(exist_ok=True)
            media.save(filename)

        if idx % 1 == 0:
            delay = random.randint(MIN_DELAY, MAX_DELAY)
            logger.info("Sleeping %d seconds to avoid rate limit...", delay)
            time.sleep(delay)


def process_reels(links: list[str]):
    for idx, link in enumerate(links, 1):
        ctype, code = extract_reel_id_from_link(link)
        if ctype != "reel":
            continue

        random_delay = random.randint(0, 5)
        logger.info("Processing %d/%d: %s", idx, len(links), code)

        video_path = f"reels/{code}.mp4"
        preview_path = f"reels_previews/{code}.jpg"
        desc_path = f"reels_descriptions/{code}.json"
        audio_path = f"reels_audio/{code}.flac"
        vsub_output = "vsub_output"
        subtitle_path = f"vsub_output/{code}.srt"
        transcript_path = f"vsub_output/{code}.txt"

        ig_request_made = False
        try:
            # only fetch if we don't already have both video + description
            if not os.path.exists(video_path) or not os.path.exists(desc_path):
                info = asyncio.run(download_reels(video_path, code))
                ig_request_made = True

                # dump out the JSON of the metadata
                with open(desc_path, "w", encoding="utf-8") as fh:
                    json.dump(to_dict_recursively(info), fh, indent=2, ensure_ascii=False)

                # pick highest‐res preview and download it
                if hasattr(info, "previews") and info.previews:
                    best = max(info.previews, key=lambda p: getattr(p, "width", 0))
                    if not os.path.exists(preview_path):
                        download_preview_image(best.url, preview_path)

            # extract audio if needed
            if not os.path.exists(audio_path) and os.path.exists(video_path):
                subprocess.run(
                    ["ffmpeg", "-i", video_path, "-ar", "16000", "-ac", "1",
                     "-map", "0:a", "-c:a", "flac", audio_path],
                    check=False
                )

            if not os.path.exists(transcript_path) or not os.path.exists(subtitle_path):
                # ensure output folder exists
                os.makedirs(vsub_output, exist_ok=True)

                cmd = [
                    VSUB_PYTHON,
                    VSUB_ENTRYPOINT,
                    video_path,
                    "-s", subtitle_path,
                    "-t", transcript_path,
                    "-o", vsub_output
                ]
                logger.info("Running vsub: %s", cmd)
                proc = subprocess.run(cmd, capture_output=True, text=True)

                logger.info("vsub stdout:\n%s", proc.stdout)
                if proc.stderr != '':
                    logger.error("vsub stderr:\n%s", proc.stderr)

            # throttle if we actually hit the API
            if ig_request_made:
                logger.info("Sleeping for %d seconds to avoid rate‐limit...", random_delay)
                time.sleep(random_delay)
                ig_request_made = False
            else:
                logger.info("Already have everything for %s, skipping.", code)

        except Exception as exc:
            logger.error("Error processing %s: %s", code, exc)
            logger.info("Sleeping for %d seconds before continuing...", random_delay)
            time.sleep(random_delay)
            continue
