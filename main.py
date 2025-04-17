import asyncio
import os
import random
import subprocess
import time
import json
from typing import List
import datetime

import requests
import logging
from outgram import Instagram
from instagram_reels.main.InstagramAPIClientImpl import InstagramAPIClientImpl
from outgram.models import InstagramPost

# Get from https://github.com/Smarandii/video_subtitler.git
VSUB_PYTHON = r"E:/Projects/python/video subtitler/.venv/Scripts/python.exe"
VSUB_ENTRYPOINT = r"E:/Projects/python/video subtitler/main.py"

# --- configure logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)


# --- Instagram client init ---
async def init_client():
    logging.info("Initializing Instagram API client for reels...")
    client = await InstagramAPIClientImpl().reels()
    logging.info("Client initialized successfully.")
    return client


# --- download video and return the full metadata object ---
async def download_reels(clip_path: str, reel_id: str):
    logging.info("Starting download for reel id: %s", reel_id)
    client = await init_client()

    logging.info("Fetching reel data…")
    info = await client.get(reel_id)
    logging.debug("Reel info received: %s", info)

    if not info.videos or not info.videos[0].url:
        logging.error("No video URL found in reel data; skipping.")
        return info

    video_url = info.videos[0].url
    logging.info("Downloading video from %s", video_url)
    resp = requests.get(video_url, stream=True)
    resp.raise_for_status()

    os.makedirs(os.path.dirname(clip_path), exist_ok=True)
    total = 0
    with open(clip_path, "wb") as f:
        for chunk in resp.iter_content(8192):
            f.write(chunk)
            total += len(chunk)
    logging.info("Saved video to %s (%d bytes)", clip_path, total)

    return info


# --- utility: extract reel ID from a URL ---
def extract_reel_id_from_link(link: str) -> (str, str):
    if "reel/" in link:
        return "reel", link.split("reel/")[1].split("/")[0]
    if "p/" in link:
        # strip off any query string
        code = link.split("p/")[1].split("/")[0]
        return "post", code
    raise ValueError(f"Can't parse reel ID from {link}")


# --- utility: deep‐convert objects with __dict__ into plain dicts ---
def to_dict_recursively(obj):
    # 1) datetime / date / time → ISO string
    if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
        # for datetime, include timezone if present
        return obj.isoformat()

    # 2) dict → recurse over values
    if isinstance(obj, dict):
        return {k: to_dict_recursively(v) for k, v in obj.items()}

    # 3) list or tuple → recurse each element
    if isinstance(obj, (list, tuple)):
        return type(obj)(to_dict_recursively(v) for v in obj)

    # 4) any object with __dict__ → recurse on its attributes
    if hasattr(obj, "__dict__"):
        return {k: to_dict_recursively(v) for k, v in vars(obj).items()}

    # 5) everything else → leave as‑is
    return obj


# --- helper to download a single preview image ---
def download_preview(url: str, dest_path: str):
    logging.info("Downloading preview image from %s", url)
    resp = requests.get(url, stream=True)
    try:
        resp.raise_for_status()
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        logging.info("Saved preview to %s", dest_path)
    except Exception as e:
        logging.error("Failed to download preview: %s", e)


if __name__ == "__main__":
    # load all reel URLs
    reel_ids: List[str] = []
    post_ids: List[str] = []
    with open("reels_links.txt", "r") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                content_type, content_id = extract_reel_id_from_link(line)
                if content_type == "reel":
                    reel_ids.append(content_id)
                else:  # "post"
                    post_ids.append(content_id)
            except ValueError:
                logging.warning("Skipping unrecognized link: %s", line)

    ig_client = Instagram()
    # First: download all POSTS (carousels, images, videos)
    for idx, post_code in enumerate(post_ids, start=1):
        logging.info("Downloading Instagram post %d/%d: %s", idx, len(post_ids), post_code)
        desc_path = f"reels_descriptions/{post_code}.json"
        try:
            if os.path.exists(desc_path):
                logging.info(f"Skipping already downloaded post: {post_code}...")
                continue
            post = ig_client.post(post_code)  # fetch metadata & all media URLs
            ig_request_made = True
            with open(desc_path, "w", encoding="utf-8") as fh:
                json.dump(to_dict_recursively(post), fh, indent=2, ensure_ascii=False)
            # Download each media (pictures/videos) in the post
            for media_index, media in enumerate(ig_client.download(post, parallel=4), start=1):
                media: InstagramPost
                ext = media.content_type.split("/")[-1].lower()
                if ext == "jpeg":
                    ext = "jpg"
                filename = f"posts/{post_code}_{media_index:03d}.{ext}"
                logging.info("  Saving %s …", filename)
                media.save(filename)
            random_delay = random.randint(5, 20)

            if ig_request_made:
                logging.info(f"Sleeping for {random_delay} seconds...")
                time.sleep(random_delay)
                ig_request_made = False
        except Exception as e:
            logging.error("Failed to download post %s: %s", post_code, e)
            continue

    for idx, reel_id in enumerate(reel_ids, start=1):
        random_delay = random.randint(0, 5)
        logging.info("Processing %d/%d: %s", idx, len(reel_ids), reel_id)

        video_path = f"reels/{reel_id}.mp4"
        preview_path = f"reels_previews/{reel_id}.jpg"
        desc_path = f"reels_descriptions/{reel_id}.json"
        audio_path = f"reels_audio/{reel_id}.flac"
        vsub_output = "vsub_output"
        subtitle_path = f"vsub_output/{reel_id}.srt"
        transcript_path = f"vsub_output/{reel_id}.txt"

        ig_request_made = False
        try:
            # only fetch if we don't already have both video + description
            if not os.path.exists(video_path) or not os.path.exists(desc_path):
                info = asyncio.run(download_reels(video_path, reel_id))
                ig_request_made = True

                # dump out the JSON of the metadata
                with open(desc_path, "w", encoding="utf-8") as fh:
                    json.dump(to_dict_recursively(info), fh, indent=2, ensure_ascii=False)

                # pick highest‐res preview and download it
                if hasattr(info, "previews") and info.previews:
                    best = max(info.previews, key=lambda p: getattr(p, "width", 0))
                    if not os.path.exists(preview_path):
                        download_preview(best.url, preview_path)

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
                logging.info("Running vsub: %s", cmd)
                proc = subprocess.run(cmd, capture_output=True, text=True)

                logging.info("vsub stdout:\n%s", proc.stdout)
                if proc.stderr != '':
                    logging.error("vsub stderr:\n%s", proc.stderr)

            # throttle if we actually hit the API
            if ig_request_made:
                logging.info("Sleeping for %d seconds to avoid rate‐limit...", random_delay)
                time.sleep(random_delay)
                ig_request_made = False
            else:
                logging.info("Already have everything for %s, skipping.", reel_id)

        except Exception as exc:
            logging.error("Error processing %s: %s", reel_id, exc)
            logging.info("Sleeping for %d seconds before continuing...", random_delay)
            time.sleep(random_delay)
            ig_request_made = False
            continue
