import asyncio
import aiohttp
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]
_UA_COUNT = len(USER_AGENTS)


class BaseChecker:
    MAX_RETRIES = 1
    RETRY_DELAY = 0.5

    def random_ua(self) -> str:
        return USER_AGENTS[random.randint(0, _UA_COUNT - 1)]

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

        _timeout = aiohttp.ClientTimeout(total=timeout)
        last_exc = None
        for attempt in range(retries + 1):
            try:
                resp = await session.request(
                    method,
                    url,
                    timeout=_timeout,
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
