import asyncio
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

if __name__ == "__main__":
    reel_id = "DBZtLTpv91b"  # Reel code extracted from the URL
    output_filename = "example.mp4"
    asyncio.run(download_reels(output_filename, reel_id))
