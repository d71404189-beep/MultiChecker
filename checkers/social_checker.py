import asyncio
import aiohttp
import re

class SocialChecker:
    PLATFORMS = {
        "telegram": {"url": "https://t.me/", "param": "username"},
        "discord": {"url": "https://discord.com/api/v9/users/", "param": "id"},
        "instagram": {"url": "https://www.instagram.com/", "param": "username"},
        "twitter": {"url": "https://twitter.com/", "param": "username"},
        "facebook": {"url": "https://www.facebook.com/", "param": "username"},
        "tiktok": {"url": "https://www.tiktok.com/@", "param": "username"},
        "reddit": {"url": "https://www.reddit.com/user/", "param": "username"},
        "linkedin": {"url": "https://www.linkedin.com/in/", "param": "username"},
    }
    
    def __init__(self):
        self.session = None
    
    async def check(self, data: str, platform: str = None, timeout: int = 10) -> dict:
        result = {
            "input": data,
            "platform": platform or "unknown",
            "valid": False,
            "exists": False,
            "info": {}
        }
        
        detected_platform = platform or self._detect_platform(data)
        result["platform"] = detected_platform
        
        if not detected_platform:
            result["info"]["error"] = "Could not detect platform"
            return result
        
        if detected_platform == "telegram":
            result = await self._check_telegram(data, timeout)
        elif detected_platform == "discord":
            result = await self._check_discord(data, timeout)
        elif detected_platform == "instagram":
            result = await self._check_instagram(data, timeout)
        elif detected_platform == "twitter":
            result = await self._check_twitter(data, timeout)
        elif detected_platform == "facebook":
            result = await self._check_facebook(data, timeout)
        elif detected_platform == "tiktok":
            result = await self._check_tiktok(data, timeout)
        elif detected_platform == "reddit":
            result = await self._check_reddit(data, timeout)
        
        return result
    
    def _detect_platform(self, data: str) -> str:
        data = data.strip().lower()
        
        if re.match(r'^@[\w\d_]{5,32}$', data):
            if "telegram" in data or len(data) < 20:
                return "telegram"
        
        if re.match(r'^[\w\d_]{2,32}$', data):
            return "instagram"
        
        if re.match(r'^t\.me/[\w\d_]+$', data):
            return "telegram"
        
        if re.match(r'^https?://', data):
            if "t.me" in data or "telegram" in data:
                return "telegram"
            elif "instagram.com" in data:
                return "instagram"
            elif "twitter.com" in data or "x.com" in data:
                return "twitter"
            elif "facebook.com" in data:
                return "facebook"
            elif "tiktok.com" in data:
                return "tiktok"
            elif "reddit.com" in data:
                return "reddit"
        
        return "instagram"
    
    async def _check_telegram(self, username: str, timeout: int) -> dict:
        result = {"input": username, "platform": "telegram", "valid": True, "exists": False, "info": {}}
        
        username = username.replace("@", "").replace("t.me/", "")
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://t.me/{username}"
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout), headers=headers) as resp:
                    result["info"]["status_code"] = resp.status
                    if resp.status == 200:
                        text = await resp.text()
                        if "If you have Telegram, you can view" not in text:
                            result["exists"] = True
                            result["info"]["message"] = "Account exists"
                        else:
                            result["info"]["message"] = "Account not found"
                    else:
                        result["info"]["message"] = f"HTTP {resp.status}"
        except asyncio.TimeoutError:
            result["info"]["error"] = "Timeout"
        except Exception as e:
            result["info"]["error"] = str(e)
        
        return result
    
    async def _check_discord(self, data: str, timeout: int) -> dict:
        result = {"input": data, "platform": "discord", "valid": True, "exists": False, "info": {}}
        return result
    
    async def _check_instagram(self, username: str, timeout: int) -> dict:
        result = {"input": username, "platform": "instagram", "valid": True, "exists": False, "info": {}}
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://www.instagram.com/{username}/"
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout), headers=headers) as resp:
                    result["info"]["status_code"] = resp.status
                    if resp.status == 200:
                        text = await resp.text()
                        if '"is_private":false' in text or '"is_private":true' in text:
                            result["exists"] = True
                            result["info"]["message"] = "Account exists"
                        elif "Page Not Found" in text:
                            result["info"]["message"] = "Account not found"
                    else:
                        result["info"]["message"] = f"HTTP {resp.status}"
        except asyncio.TimeoutError:
            result["info"]["error"] = "Timeout"
        except Exception as e:
            result["info"]["error"] = str(e)
        
        return result
    
    async def _check_twitter(self, username: str, timeout: int) -> dict:
        result = {"input": username, "platform": "twitter", "valid": True, "exists": False, "info": {}}
        return result
    
    async def _check_facebook(self, username: str, timeout: int) -> dict:
        result = {"input": username, "platform": "facebook", "valid": True, "exists": False, "info": {}}
        return result
    
    async def _check_tiktok(self, username: str, timeout: int) -> dict:
        result = {"input": username, "platform": "tiktok", "valid": True, "exists": False, "info": {}}
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://www.tiktok.com/@{username}"
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout), headers=headers) as resp:
                    result["info"]["status_code"] = resp.status
                    if resp.status == 200:
                        result["exists"] = True
                        result["info"]["message"] = "Account exists"
                    else:
                        result["info"]["message"] = "Account not found"
        except Exception as e:
            result["info"]["error"] = str(e)
        
        return result
    
    async def _check_reddit(self, username: str, timeout: int) -> dict:
        result = {"input": username, "platform": "reddit", "valid": True, "exists": False, "info": {}}
        return result
