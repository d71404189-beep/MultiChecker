import asyncio
import aiohttp
import re

from checkers.base_checker import BaseChecker


class AIChecker(BaseChecker):
    SERVICES = {
        "chatgpt": "ChatGPT/OpenAI",
        "gemini": "Google Gemini",
        "claude": "Claude/Anthropic",
        "midjourney": "Midjourney",
        "character_ai": "Character AI",
        "perplexity": "Perplexity AI",
        "huggingface": "Hugging Face",
        "replicate": "Replicate",
        "stable_diffusion": "Stable Diffusion",
    }

    async def check(self, data: str, service: str = None, timeout: int = 10, proxy: str = None, session: aiohttp.ClientSession = None) -> dict:
        result = self.make_result(input=data, service=service or "unknown")

        if "@" in data:
            detected = service or "chatgpt"
        else:
            detected = self._detect_service(data) or service or "chatgpt"

        result["service"] = detected

        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession()

        try:
            handler = {
                "chatgpt": self._check_openai,
                "gemini": self._check_gemini,
                "claude": self._check_claude,
                "midjourney": self._check_midjourney,
                "character_ai": self._check_character_ai,
                "perplexity": self._check_perplexity,
                "huggingface": self._check_huggingface,
                "replicate": self._check_replicate,
                "stable_diffusion": self._check_stable_diffusion,
            }.get(detected)

            if handler:
                result = await handler(data, timeout, proxy, session)
            else:
                result["info"]["error"] = f"No checker for {detected}"
        finally:
            if own_session:
                await session.close()

        return result

    def _detect_service(self, data: str) -> str:
        data_lower = data.lower()
        mapping = {
            "openai": "chatgpt", "chatgpt": "chatgpt",
            "google": "gemini", "gemini": "gemini",
            "claude": "claude", "anthropic": "claude",
            "midjourney": "midjourney",
            "character.ai": "character_ai", "character ai": "character_ai",
            "perplexity": "perplexity",
            "huggingface": "huggingface", "hugging face": "huggingface",
            "replicate": "replicate",
            "stable diffusion": "stable_diffusion", "civitai": "stable_diffusion",
        }
        for keyword, svc in mapping.items():
            if keyword in data_lower:
                return svc
        return None

    async def _check_openai(self, email, timeout, proxy, session):
        result = self.make_result(input=email, service="chatgpt", valid=True)
        try:
            url = "https://auth0.openai.com/u/signup/identifier"
            resp = await self.fetch(session, "POST", url, timeout=timeout, proxy=proxy,
                                    json={"email": email, "app": "chatgpt"},
                                    headers={"Content-Type": "application/json"})
            status = resp.status
            text = await resp.text()
            resp.close()
            if status == 200:
                if "already" in text.lower() or "exists" in text.lower():
                    result["exists"] = True
                    result["info"]["message"] = "OpenAI account likely exists"
                else:
                    result["info"]["message"] = "Account may not exist or signup available"
            elif status == 302 or status == 303:
                result["exists"] = True
                result["info"]["message"] = "OpenAI account likely exists (redirect)"
            elif status == 400:
                if "already" in text.lower():
                    result["exists"] = True
                    result["info"]["message"] = "Email already registered"
                else:
                    result["info"]["message"] = "Could not determine account status"
            else:
                result["info"]["message"] = f"HTTP {status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_gemini(self, email, timeout, proxy, session):
        result = self.make_result(input=email, service="gemini", valid=True)
        try:
            url = "https://accounts.google.com/AccountChooser"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy,
                                    params={"Email": email, "flowName": "GlifWebSignIn"})
            text = await resp.text()
            resp.close()
            if "couldn't find your google account" in text.lower():
                result["info"]["message"] = "Google account not found"
            else:
                result["exists"] = True
                result["info"]["message"] = "Google account likely exists (Gemini access possible)"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_claude(self, email, timeout, proxy, session):
        result = self.make_result(input=email, service="claude", valid=True)
        try:
            url = "https://claude.ai/login"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            status = resp.status
            resp.close()
            if status == 200:
                result["info"]["message"] = "Claude login page accessible"
            else:
                result["info"]["message"] = f"HTTP {status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_midjourney(self, username, timeout, proxy, session):
        result = self.make_result(input=username, service="midjourney", valid=True)
        try:
            url = f"https://www.midjourney.com/app/users/{username}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            status = resp.status
            resp.close()
            if status == 200:
                result["exists"] = True
                result["info"]["message"] = "Midjourney profile page loaded"
            elif status == 404:
                result["info"]["message"] = "Profile not found"
            else:
                result["info"]["message"] = f"HTTP {status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_character_ai(self, username, timeout, proxy, session):
        result = self.make_result(input=username, service="character_ai", valid=True)
        try:
            url = f"https://character.ai/profile/{username}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            status = resp.status
            text = await resp.text()
            resp.close()
            if status == 200:
                if "not found" in text.lower() or "404" in text:
                    result["info"]["message"] = "Profile not found"
                else:
                    result["exists"] = True
                    result["info"]["message"] = "Character AI profile found"
            elif status == 404:
                result["info"]["message"] = "Profile not found"
            else:
                result["info"]["message"] = f"HTTP {status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_perplexity(self, email, timeout, proxy, session):
        result = self.make_result(input=email, service="perplexity", valid=True)
        try:
            url = "https://www.perplexity.ai/api/auth/signin/email"
            resp = await self.fetch(session, "POST", url, timeout=timeout, proxy=proxy,
                                    json={"email": email},
                                    headers={"Content-Type": "application/json"})
            status = resp.status
            resp.close()
            if status == 200:
                result["info"]["message"] = "Perplexity endpoint responded (magic link flow)"
            elif status == 302:
                result["exists"] = True
                result["info"]["message"] = "Perplexity account likely exists"
            else:
                result["info"]["message"] = f"HTTP {status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_huggingface(self, username, timeout, proxy, session):
        result = self.make_result(input=username, service="huggingface", valid=True)
        clean = username.strip().lstrip("@")
        try:
            url = f"https://huggingface.co/api/users/{clean}/overview"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            status = resp.status
            if status == 200:
                data = await resp.json()
                resp.close()
                result["exists"] = True
                result["info"]["message"] = "Hugging Face user exists"
                result["info"]["fullname"] = data.get("fullname", "")
            else:
                resp.close()
                if status == 404:
                    result["info"]["message"] = "User not found"
                else:
                    result["info"]["message"] = f"HTTP {status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_replicate(self, username, timeout, proxy, session):
        result = self.make_result(input=username, service="replicate", valid=True)
        clean = username.strip().lstrip("@")
        try:
            url = f"https://replicate.com/{clean}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            status = resp.status
            resp.close()
            if status == 200:
                result["exists"] = True
                result["info"]["message"] = "Replicate profile found"
            elif status == 404:
                result["info"]["message"] = "Profile not found"
            else:
                result["info"]["message"] = f"HTTP {status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_stable_diffusion(self, username, timeout, proxy, session):
        result = self.make_result(input=username, service="stable_diffusion", valid=True)
        clean = username.strip().lstrip("@")
        try:
            url = f"https://civitai.com/api/v1/users?query={clean}&limit=1"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            status = resp.status
            if status == 200:
                data = await resp.json()
                resp.close()
                items = data.get("items", [])
                if items and items[0].get("username", "").lower() == clean.lower():
                    result["exists"] = True
                    result["info"]["message"] = "CivitAI user found"
                else:
                    result["info"]["message"] = "User not found on CivitAI"
            else:
                resp.close()
                result["info"]["message"] = f"HTTP {status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result
