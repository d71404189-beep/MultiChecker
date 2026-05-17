import asyncio
import aiohttp
import random

# Опциональная поддержка SOCKS прокси
try:
    from aiohttp_socks import ProxyConnector, ProxyType
    SOCKS_AVAILABLE = True
except ImportError:
    SOCKS_AVAILABLE = False
    ProxyConnector = None
    ProxyType = None

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
    
    def _parse_proxy(self, proxy: str) -> tuple:
        """
        Парсит прокси строку и определяет тип
        
        Поддерживаемые форматы:
        - http://ip:port
        - https://ip:port
        - socks4://ip:port
        - socks5://ip:port
        - socks4://user:pass@ip:port
        - socks5://user:pass@ip:port
        - ip:port (по умолчанию http)
        
        Returns:
            (proxy_type, proxy_url) или (None, proxy) если не SOCKS
        """
        if not proxy:
            return None, None
        
        proxy = proxy.strip()
        
        # Определяем тип прокси
        if proxy.startswith("socks4://"):
            return "socks4", proxy
        elif proxy.startswith("socks5://"):
            return "socks5", proxy
        elif proxy.startswith("http://") or proxy.startswith("https://"):
            return "http", proxy
        else:
            # Если нет протокола - считаем http
            return "http", f"http://{proxy}"
    
    def _create_socks_connector(self, proxy: str) -> ProxyConnector:
        """Создает SOCKS connector для aiohttp"""
        if not SOCKS_AVAILABLE:
            raise ImportError(
                "aiohttp-socks не установлен. "
                "Установите: pip install aiohttp-socks"
            )
        
        proxy_type, proxy_url = self._parse_proxy(proxy)
        
        if proxy_type == "socks4":
            # socks4://ip:port или socks4://user:pass@ip:port
            return ProxyConnector.from_url(proxy_url)
        elif proxy_type == "socks5":
            # socks5://ip:port или socks5://user:pass@ip:port
            return ProxyConnector.from_url(proxy_url)
        else:
            return None

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
        
        # По умолчанию SSL=True для безопасности. Может переопределяться через kwargs при вызове.
        ssl_verify = kwargs.pop("ssl", True)
        
        # Определяем тип прокси
        proxy_type, proxy_url = self._parse_proxy(proxy) if proxy else (None, None)
        
        # Если SOCKS прокси - создаем специальную сессию
        if proxy_type in ["socks4", "socks5"]:
            if not SOCKS_AVAILABLE:
                raise ImportError(
                    f"Для использования {proxy_type.upper()} прокси установите: "
                    "pip install aiohttp-socks"
                )
            
            # Создаем новую сессию с SOCKS connector
            connector = self._create_socks_connector(proxy)
            async with aiohttp.ClientSession(connector=connector) as socks_session:
                last_exc = None
                for attempt in range(retries + 1):
                    try:
                        resp = await socks_session.request(
                            method,
                            url,
                            timeout=_timeout,
                            headers=_headers,
                            ssl=ssl_verify,
                            **kwargs,
                        )
                        return resp
                    except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                        last_exc = e
                        if attempt < retries:
                            await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                raise last_exc
        else:
            # HTTP/HTTPS прокси - используем стандартный способ
            last_exc = None
            for attempt in range(retries + 1):
                try:
                    resp = await session.request(
                        method,
                        url,
                        timeout=_timeout,
                        proxy=proxy_url if proxy_url else None,
                        headers=_headers,
                        ssl=ssl_verify,
                        **kwargs,
                    )
                    return resp
                except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                    last_exc = e
                    if attempt < retries:
                        await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
            raise last_exc
