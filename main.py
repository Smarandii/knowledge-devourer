import asyncio
import os.path
import random
import subprocess
import time

import requests
import logging
from instagram_reels.main.InstagramAPIClientImpl import InstagramAPIClientImpl

# Configure logging for detailed output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s'
)


async def init_client():
    logging.info("Initializing Instagram API client for reels...")
    client = await InstagramAPIClientImpl().reels()
    logging.info("Client initialized successfully.")
    return client


async def download_reels(clip_name: str, reel_id: str):
    logging.info("Starting download for reel id: %s", reel_id)
    client = await init_client()
    
    logging.info("Fetching reel data...")
    info = await client.get(reel_id)
    logging.debug("Reel info received: %s", info)
    
    # Check if we have any video URL
    if not info.videos or not info.videos[0].url:
        logging.error("No video URL found in the reel data.")
        return
    
    video_url = info.videos[0].url
    logging.info("Video URL found: %s", video_url)
    
    # Download the video using a streaming request
    logging.info("Downloading video from %s", video_url)
    response = requests.get(video_url, stream=True)
    if response.status_code != 200:
        logging.error("Failed to download video. Status code: %s", response.status_code)
        return

    total_bytes = 0
    with open(clip_name, "wb+") as out_file:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                out_file.write(chunk)
                total_bytes += len(chunk)
    logging.info("Video downloaded successfully and saved as '%s' (%d bytes)", clip_name, total_bytes)
    return info


def extract_reel_id_from_link(reel_link: str) -> str:
    # https://www.instagram.com/reel/DDVav1xSJhL/?igsh=MXhwazBhNWFzMzE0Nw==
    if "reel" in reel_link:
        return reel_link.split("reel/")[1].split("/")[0]
    if "p" in reel_link:
        return reel_link.split("p/")[1].split("/")[0]


if __name__ == "__main__":
    reels_id = []
    with open('reels_links.txt', 'r') as f:
        for line in f.readlines():
            reels_id.append(extract_reel_id_from_link(line))

    ig_request_made = False
    for i, reel_id in enumerate(reels_id):
        try:
            print(f"Downloading {i + 1} out of {len(reels_id)}...")
            output_filename = f"./reels/{reel_id}.mp4"
            reel_description_file = f"./reels_descriptions/{reel_id}.txt"
            output_audio_filename = f"./reels_audio/{reel_id}.flac"

            random_delay = random.randint(10, 20)

            # if not os.path.exists(output_filename) or not os.path.exists(reel_description_file):
            #     reel_info = asyncio.run(download_reels(output_filename, reel_id))
            #     ig_request_made = True
            #
            #     with open(reel_description_file, "w") as f:
            #         f.write(str(reel_info))

            if not os.path.exists(output_audio_filename) and os.path.exists(output_filename):
                subprocess.run(f"ffmpeg -i {output_filename} -ar 16000 -ac 1 -map 0:a -c:a flac {output_audio_filename}")

            if ig_request_made:
                print(f"Sleeping for {random_delay} seconds...")
                time.sleep(random_delay)
                ig_request_made = False
            else:
                print(f"Already downloaded {reel_id}...")
        except Exception as e:
            print(f"Error while downloading reel {reel_id}...")
            print(f"Sleeping for {random_delay} seconds...")
            time.sleep(random_delay)
            ig_request_made = False
            continue
