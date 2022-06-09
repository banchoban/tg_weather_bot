import aiohttp
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)


async def make_request(url: str, headers=None, payload=None):
    """Default method for making HTTP requests"""
    try_count = 0

    while try_count < 4:
        try:
            if not payload:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url=url, headers=headers, timeout=10) as response:

                        text = await response.text()

                        return text
            else:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url=url, headers=headers, data=payload, timeout=10) as response:

                        text = await response.text()

                        return text
        except Exception as error:
            logger.error(f'Error on request to {url}: {type(error)} {error}')

    logger.warning(f'Could not make request to {url}. More than 5 errors.')
