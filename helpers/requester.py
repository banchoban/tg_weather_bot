import aiohttp


async def make_request(url: str, payload=None):
    """Default method for making HTTP requests"""

    if not payload:
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, timeout=10) as response:

                text = await response.text()

                return text
    else:
        return  # TODO POST request
