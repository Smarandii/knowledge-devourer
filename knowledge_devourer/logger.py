import logging


def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s %(levelname)s: %(message)s",
    )
    return logging.getLogger(__name__)
