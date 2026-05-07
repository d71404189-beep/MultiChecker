import asyncio
import aiohttp
import re

from checkers.base_checker import BaseChecker


class SocialChecker(BaseChecker):
    PLATFORMS = {
        "telegram": {"url": "https://t.me/", "param": "username"},
        "discord": {"url": "https://discord.com/api/v10/users/", "param": "id"},
        "instagram": {"url": "https://www.instagram.com/", "param": "username"},
        "twitter": {"url": "https://x.com/", "param": "username"},
        "facebook": {"url": "https://www.facebook.com/", "param": "username"},
        "tiktok": {"url": "https://www.tiktok.com/@", "param": "username"},
        "reddit": {"url": "https://www.reddit.com/user/", "param": "username"},
        "github": {"url": "https://api.github.com/users/", "param": "username"},
        "vk": {"url": "https://vk.com/", "param": "username"},
    }

    async def check(self, data: str, platform: str = None, timeout: int = 10, proxy: str = None, session: aiohttp.ClientSession = None) -> dict:
        result = self.make_result(input=data, platform=platform or "unknown")

        detected_platform = platform or self._detect_platform(data)
        result["platform"] = detected_platform

        if not detected_platform:
            result["info"]["error"] = "Could not detect platform"
            return result

        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession()

        try:
            handler = {
                "telegram": self._check_telegram,
                "discord": self._check_discord,
                "instagram": self._check_instagram,
                "twitter": self._check_twitter,
                "facebook": self._check_facebook,
                "tiktok": self._check_tiktok,
                "reddit": self._check_reddit,
                "github": self._check_github,
                "vk": self._check_vk,
            }.get(detected_platform)

            if handler:
                result = await handler(data, timeout, proxy, session)
            else:
                result["info"]["error"] = f"No checker for {detected_platform}"
        finally:
            if own_session:
                await session.close()

        return result

    def _detect_platform(self, data: str) -> str:
        data_stripped = data.strip()
        data_lower = data_stripped.lower()

        if re.match(r'^https?://', data_lower):
            if "t.me" in data_lower or "telegram" in data_lower:
                return "telegram"
            elif "instagram.com" in data_lower:
                return "instagram"
            elif "twitter.com" in data_lower or "x.com" in data_lower:
                return "twitter"
            elif "facebook.com" in data_lower or "fb.com" in data_lower:
                return "facebook"
            elif "tiktok.com" in data_lower:
                return "tiktok"
            elif "reddit.com" in data_lower:
                return "reddit"
            elif "github.com" in data_lower:
                return "github"
            elif "vk.com" in data_lower:
                return "vk"
            elif "discord" in data_lower:
                return "discord"

        if data_stripped.startswith("t.me/"):
            return "telegram"

        if re.match(r'^@[\w\d_]{1,32}$', data_stripped):
            return "telegram"

        if re.match(r'^\d{17,20}$', data_stripped):
            return "discord"

        if re.match(r'^[\w\d_.]{1,30}$', data_stripped):
            return "instagram"

        return "instagram"

    @staticmethod
    def _extract_username(data: str) -> str:
        data = data.strip().rstrip("/")
        if data.startswith("@"):
            return data[1:]
        if "://" in data:
            parts = data.split("/")
            for part in reversed(parts):
                if part and not part.startswith("http") and "." in part is False:
                    clean = part.lstrip("@")
                    if clean:
                        return clean
            return parts[-1].lstrip("@") if parts[-1] else data
        return data

    async def _check_telegram(self, username, timeout, proxy, session):
        result = self.make_result(input=username, platform="telegram", valid=True)
        clean = self._extract_username(username).replace("t.me/", "").replace("@", "")
        try:
            url = f"https://t.me/{clean}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            text = await resp.text()
            resp.close()
            if resp.status == 200:
                if 'class="tgme_page_title"' in text or "tgme_page_photo" in text:
                    result["exists"] = True
                    result["info"]["message"] = "Account exists"
                else:
                    result["info"]["message"] = "Account not found"
            else:
                result["info"]["message"] = f"HTTP {resp.status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_discord(self, data, timeout, proxy, session):
        result = self.make_result(input=data, platform="discord", valid=True)
        user_id = self._extract_username(data)
        try:
            url = f"https://discord.com/api/v10/users/{user_id}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy,
                                    headers={"Content-Type": "application/json"})
            status = resp.status
            resp.close()
            if status == 200:
                result["exists"] = True
                result["info"]["message"] = "Discord user exists"
            elif status == 401:
                result["info"]["message"] = "Auth required (ID format valid)"
            elif status == 404:
                result["info"]["message"] = "User not found"
            else:
                result["info"]["message"] = f"HTTP {status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_instagram(self, username, timeout, proxy, session):
        result = self.make_result(input=username, platform="instagram", valid=True)
        clean = self._extract_username(username)
        try:
            url = f"https://www.instagram.com/{clean}/"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            text = await resp.text()
            status = resp.status
            resp.close()
            if status == 200:
                if '"is_private"' in text or '"edge_followed_by"' in text:
                    result["exists"] = True
                    result["info"]["message"] = "Account exists"
                elif "Page Not Found" in text or "page isn't available" in text.lower():
                    result["info"]["message"] = "Account not found"
                else:
                    result["exists"] = True
                    result["info"]["message"] = "Profile page loaded"
            elif status == 404:
                result["info"]["message"] = "Account not found"
            else:
                result["info"]["message"] = f"HTTP {status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_twitter(self, username, timeout, proxy, session):
        result = self.make_result(input=username, platform="twitter", valid=True)
        clean = self._extract_username(username)
        try:
            url = f"https://x.com/{clean}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            status = resp.status
            text = await resp.text()
            resp.close()
            if status == 200:
                if "This account doesn" in text or "Account suspended" in text:
                    result["info"]["message"] = "Account suspended or does not exist"
                else:
                    result["exists"] = True
                    result["info"]["message"] = "Account exists"
            elif status == 404:
                result["info"]["message"] = "Account not found"
            elif status in (302, 301):
                result["exists"] = True
                result["info"]["message"] = "Account exists (redirect)"
            else:
                result["info"]["message"] = f"HTTP {status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_facebook(self, username, timeout, proxy, session):
        result = self.make_result(input=username, platform="facebook", valid=True)
        clean = self._extract_username(username)
        try:
            url = f"https://www.facebook.com/{clean}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            status = resp.status
            text = await resp.text()
            resp.close()
            if status == 200:
                if "page_not_found" in text.lower() or "this page isn" in text.lower():
                    result["info"]["message"] = "Page not found"
                else:
                    result["exists"] = True
                    result["info"]["message"] = "Facebook profile exists"
            elif status == 404:
                result["info"]["message"] = "Profile not found"
            else:
                result["info"]["message"] = f"HTTP {status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_tiktok(self, username, timeout, proxy, session):
        result = self.make_result(input=username, platform="tiktok", valid=True)
        clean = self._extract_username(username)
        try:
            url = f"https://www.tiktok.com/@{clean}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            status = resp.status
            text = await resp.text()
            resp.close()
            if status == 200:
                if '"statusCode":10202' in text or "Couldn't find this account" in text:
                    result["info"]["message"] = "Account not found"
                else:
                    result["exists"] = True
                    result["info"]["message"] = "Account exists"
            elif status == 404:
                result["info"]["message"] = "Account not found"
            else:
                result["info"]["message"] = f"HTTP {status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_reddit(self, username, timeout, proxy, session):
        result = self.make_result(input=username, platform="reddit", valid=True)
        clean = self._extract_username(username)
        try:
            url = f"https://www.reddit.com/user/{clean}/about.json"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            status = resp.status
            if status == 200:
                data = await resp.json()
                resp.close()
                if data.get("kind") == "t2":
                    result["exists"] = True
                    result["info"]["message"] = "Reddit user exists"
                    result["info"]["karma"] = data.get("data", {}).get("total_karma", 0)
                else:
                    result["info"]["message"] = "User not found"
            else:
                resp.close()
                result["info"]["message"] = "User not found" if status == 404 else f"HTTP {status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_github(self, username, timeout, proxy, session):
        result = self.make_result(input=username, platform="github", valid=True)
        clean = self._extract_username(username)
        try:
            url = f"https://api.github.com/users/{clean}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            status = resp.status
            if status == 200:
                data = await resp.json()
                resp.close()
                result["exists"] = True
                result["info"]["message"] = "GitHub user exists"
                result["info"]["public_repos"] = data.get("public_repos", 0)
                result["info"]["followers"] = data.get("followers", 0)
            else:
                resp.close()
                result["info"]["message"] = "User not found" if status == 404 else f"HTTP {status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_vk(self, username, timeout, proxy, session):
        result = self.make_result(input=username, platform="vk", valid=True)
        clean = self._extract_username(username)
        try:
            url = f"https://vk.com/{clean}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            status = resp.status
            text = await resp.text()
            resp.close()
            if status == 200:
                if "Profile deleted" in text or "page_not_found" in text.lower():
                    result["info"]["message"] = "Profile deleted or not found"
                else:
                    result["exists"] = True
                    result["info"]["message"] = "VK profile exists"
            elif status == 404:
                result["info"]["message"] = "Profile not found"
            else:
                result["info"]["message"] = f"HTTP {status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result
