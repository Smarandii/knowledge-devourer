import sys
from processor import process_posts, process_reels
from logger import setup_logging

logger = setup_logging()


def load_links(path: str) -> list[str]:
    with open(path, "r") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]


def main():
    if len(sys.argv) < 2:
        logger.error("Usage: python -m reels_download_tool <links_file>")
        sys.exit(1)

    links = load_links(sys.argv[1])
    process_posts(links)  # handle /p/ links
    process_reels(links)  # handle /reel/ links


if __name__ == "__main__":
    main()
