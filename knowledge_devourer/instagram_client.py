from outgram import Instagram
from instagram_reels.main.InstagramAPIClientImpl import InstagramAPIClientImpl


async def init_reels_client():
    client = await InstagramAPIClientImpl().reels()
    return client


def get_instagram_client():
    return Instagram()
