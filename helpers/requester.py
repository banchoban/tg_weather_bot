import aiohttp


async def make_request(url: str, headers=None, payload=None):
    """Default method for making HTTP requests"""

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
