import asyncio
import aiohttp
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]


class BaseChecker:
    MAX_RETRIES = 2
    RETRY_DELAY = 1.0

    def random_ua(self) -> str:
        return random.choice(USER_AGENTS)

    def make_result(self, **kwargs) -> dict:
        base = {
            "input": "",
            "valid": False,
            "exists": False,
            "info": {},
        }
        base.update(kwargs)
        return base

    async def fetch(
        self,
        session: aiohttp.ClientSession,
        method: str,
        url: str,
        timeout: int = 10,
        proxy: str = None,
        headers: dict = None,
        retries: int = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        if retries is None:
            retries = self.MAX_RETRIES

        _headers = {"User-Agent": self.random_ua()}
        if headers:
            _headers.update(headers)

        last_exc = None
        for attempt in range(retries + 1):
            try:
                resp = await session.request(
                    method,
                    url,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                    proxy=proxy,
                    headers=_headers,
                    ssl=False,
                    **kwargs,
                )
                return resp
            except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                last_exc = e
                if attempt < retries:
                    await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
        raise last_exc
