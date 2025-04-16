import asyncio
import os
import random
import subprocess
import time
import json
import requests
import logging
from instagram_reels.main.InstagramAPIClientImpl import InstagramAPIClientImpl

VSUB_PATH = os.getenv("VSUB_PATH", r"E:/Projects/python/video subtitler/.venv/Scripts/python.exe "
                       r"E:/Projects/python/video subtitler/main.py")

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
def extract_reel_id_from_link(link: str) -> str:
    if "reel/" in link:
        return link.split("reel/")[1].split("/")[0]
    if "p/" in link:
        return link.split("p/")[1].split("/")[0]
    raise ValueError(f"Can't parse reel ID from {link}")


# --- utility: deep‐convert objects with __dict__ into plain dicts ---
def to_dict_recursively(obj):
    if isinstance(obj, dict):
        return {k: to_dict_recursively(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return type(obj)(to_dict_recursively(v) for v in obj)
    elif hasattr(obj, "__dict__"):
        return {k: to_dict_recursively(v) for k, v in vars(obj).items()}
    else:
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


# --- entry point ---
if __name__ == "__main__":
    # load all reel URLs
    reel_ids = []
    with open("reels_links.txt", "r") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                reel_ids.append(extract_reel_id_from_link(line))
            except ValueError:
                logging.warning("Skipping unrecognized link: %s", line)

    ig_request_made = False

    for idx, reel_id in enumerate(reel_ids, start=1):
        random_delay = random.randint(10, 20)
        logging.info("Processing %d/%d: %s", idx, len(reel_ids), reel_id)

        video_path = f"reels/{reel_id}.mp4"
        preview_path = f"reels_previews/{reel_id}.jpg"
        desc_path = f"reels_descriptions/{reel_id}.json"
        audio_path = f"reels_audio/{reel_id}.flac"
        vsub_output = "vsub_output"
        subtitle_path = f"vsub_output/{reel_id}.srt"
        transcript_path = f"vsub_output/{reel_id}.txt"

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
                subprocess.run(
                    [VSUB_PATH, audio_path, "-o", vsub_output],
                    check=False
                )

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
