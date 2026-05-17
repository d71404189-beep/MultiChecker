import asyncio
import aiohttp
import re
import json
import csv
import os
from datetime import datetime

from checkers.base_checker import BaseChecker
# v1.0.81: Интеграция новых модулей
from checkers.ai_subscription_checker import global_subscription_checker
from checkers.ai_api_validator import global_api_validator


class AIChecker(BaseChecker):
    def __init__(self):
        # v1.0.81: Расширенный список сервисов (30+)
        self.auth_info = {
            # Chat AI
            "chatgpt": {
                "auth_type": "Email + Пароль / Google / Microsoft / Apple",
                "wallets": "Web (chat.openai.com), ChatGPT App",
                "how": "Открой chat.openai.com, войди через email/пароль или Google/Microsoft/Apple",
                "subscription_tiers": ["Free", "Plus ($20/мес)", "Team ($25/мес)", "Enterprise ($60/мес)"],
            },
            "gemini": {
                "auth_type": "Google аккаунт (Email + Пароль)",
                "wallets": "Web (gemini.google.com), Google App",
                "how": "Открой gemini.google.com, войди через Google аккаунт",
                "subscription_tiers": ["Free", "Advanced ($19.99/мес)"],
            },
            "claude": {
                "auth_type": "Email + Пароль / Google",
                "wallets": "Web (claude.ai), Claude App",
                "how": "Открой claude.ai, войди через email/пароль или Google аккаунт",
                "subscription_tiers": ["Free", "Pro ($20/мес)"],
            },
            "grok": {
                "auth_type": "Twitter/X аккаунт",
                "wallets": "Web (x.com), X App",
                "how": "Открой x.com, войди через Twitter аккаунт, доступ к Grok для Premium+ подписчиков",
                "subscription_tiers": ["Premium+ ($16/мес)"],
            },
            "pi": {
                "auth_type": "Email + Пароль / Google / Apple",
                "wallets": "Web (pi.ai), Pi App",
                "how": "Открой pi.ai, войди через email, Google или Apple",
                "subscription_tiers": ["Free"],
            },
            "poe": {
                "auth_type": "Email + Пароль / Google / Apple",
                "wallets": "Web (poe.com), Poe App",
                "how": "Открой poe.com, войди через email, Google или Apple",
                "subscription_tiers": ["Free", "Premium ($19.99/мес)"],
            },
            
            # Image Generation
            "midjourney": {
                "auth_type": "Discord аккаунт",
                "wallets": "Discord, Web (midjourney.com)",
                "how": "Войди в Discord, присоединись к серверу Midjourney или используй midjourney.com",
                "subscription_tiers": ["Basic ($10/мес)", "Standard ($30/мес)", "Pro ($60/мес)", "Mega ($120/мес)"],
            },
            "leonardo": {
                "auth_type": "Email + Пароль / Google",
                "wallets": "Web (leonardo.ai)",
                "how": "Открой leonardo.ai, войди через email или Google",
                "subscription_tiers": ["Free", "Apprentice ($10/мес)", "Artisan ($24/мес)", "Maestro ($48/мес)"],
            },
            "ideogram": {
                "auth_type": "Email + Пароль / Google",
                "wallets": "Web (ideogram.ai)",
                "how": "Открой ideogram.ai, войди через email или Google",
                "subscription_tiers": ["Free", "Plus ($8/мес)", "Pro ($20/мес)"],
            },
            "playground": {
                "auth_type": "Email + Пароль / Google",
                "wallets": "Web (playgroundai.com)",
                "how": "Открой playgroundai.com, войди через email или Google",
                "subscription_tiers": ["Free", "Pro ($15/мес)"],
            },
            "dalle": {
                "auth_type": "OpenAI аккаунт",
                "wallets": "Web (labs.openai.com), ChatGPT Plus",
                "how": "Открой labs.openai.com или используй через ChatGPT Plus",
                "subscription_tiers": ["Pay-per-use", "ChatGPT Plus ($20/мес)"],
            },
            
            # Video AI
            "runway": {
                "auth_type": "Email + Пароль / Google",
                "wallets": "Web (runwayml.com)",
                "how": "Открой runwayml.com, войди через email или Google",
                "subscription_tiers": ["Free", "Standard ($12/мес)", "Pro ($28/мес)", "Unlimited ($76/мес)"],
            },
            "pika": {
                "auth_type": "Email + Пароль / Google / Discord",
                "wallets": "Web (pika.art), Discord",
                "how": "Открой pika.art или используй Discord бот",
                "subscription_tiers": ["Free", "Standard ($10/мес)", "Unlimited ($35/мес)"],
            },
            "synthesia": {
                "auth_type": "Email + Пароль",
                "wallets": "Web (synthesia.io)",
                "how": "Открой synthesia.io, создай аккаунт",
                "subscription_tiers": ["Starter ($22/мес)", "Creator ($67/мес)"],
            },
            "heygen": {
                "auth_type": "Email + Пароль / Google",
                "wallets": "Web (heygen.com)",
                "how": "Открой heygen.com, войди через email или Google",
                "subscription_tiers": ["Free", "Creator ($24/мес)", "Business ($120/мес)"],
            },
            
            # Voice AI
            "elevenlabs": {
                "auth_type": "Email + Пароль / Google",
                "wallets": "Web (elevenlabs.io)",
                "how": "Открой elevenlabs.io, войди через email или Google",
                "subscription_tiers": ["Free", "Starter ($5/мес)", "Creator ($22/мес)", "Pro ($99/мес)", "Scale ($330/мес)"],
            },
            "murf": {
                "auth_type": "Email + Пароль / Google",
                "wallets": "Web (murf.ai)",
                "how": "Открой murf.ai, войди через email или Google",
                "subscription_tiers": ["Free", "Basic ($19/мес)", "Pro ($26/мес)"],
            },
            "playht": {
                "auth_type": "Email + Пароль / Google",
                "wallets": "Web (play.ht)",
                "how": "Открой play.ht, войди через email или Google",
                "subscription_tiers": ["Free", "Creator ($31.20/мес)", "Pro ($79.20/мес)"],
            },
            
            # Music AI
            "suno": {
                "auth_type": "Email + Пароль / Google / Discord",
                "wallets": "Web (suno.ai), Discord",
                "how": "Открой suno.ai или используй Discord бот",
                "subscription_tiers": ["Free", "Pro ($10/мес)", "Premier ($30/мес)"],
            },
            "udio": {
                "auth_type": "Email + Пароль / Google",
                "wallets": "Web (udio.com)",
                "how": "Открой udio.com, войди через email или Google",
                "subscription_tiers": ["Free", "Standard ($10/мес)", "Pro ($30/мес)"],
            },
            "mubert": {
                "auth_type": "Email + Пароль / Google",
                "wallets": "Web (mubert.com)",
                "how": "Открой mubert.com, войди через email или Google",
                "subscription_tiers": ["Free", "Pro ($14/мес)"],
            },
            
            # Code AI
            "github_copilot": {
                "auth_type": "GitHub аккаунт",
                "wallets": "VS Code, JetBrains IDEs, GitHub.com",
                "how": "Установи расширение в IDE, войди через GitHub",
                "subscription_tiers": ["Individual ($10/мес)", "Business ($19/мес)"],
            },
            "cursor": {
                "auth_type": "Email + Пароль / Google / GitHub",
                "wallets": "Cursor IDE",
                "how": "Скачай Cursor IDE с cursor.sh, войди через email/Google/GitHub",
                "subscription_tiers": ["Free", "Pro ($20/мес)"],
            },
            "tabnine": {
                "auth_type": "Email + Пароль / Google / GitHub",
                "wallets": "VS Code, JetBrains IDEs",
                "how": "Установи расширение Tabnine в IDE",
                "subscription_tiers": ["Free", "Pro ($12/мес)"],
            },
            "codeium": {
                "auth_type": "Email + Пароль / Google / GitHub",
                "wallets": "VS Code, JetBrains IDEs",
                "how": "Установи расширение Codeium в IDE",
                "subscription_tiers": ["Free", "Pro ($10/мес)"],
            },
            "replit": {
                "auth_type": "Email + Пароль / Google / GitHub",
                "wallets": "Web (replit.com)",
                "how": "Открой replit.com, войди через email/Google/GitHub",
                "subscription_tiers": ["Free", "Hacker ($7/мес)", "Pro ($20/мес)"],
            },
            
            # Productivity
            "notion": {
                "auth_type": "Email + Пароль / Google / Apple",
                "wallets": "Web (notion.so), Notion App",
                "how": "Открой notion.so, войди через email/Google/Apple",
                "subscription_tiers": ["Free", "Plus ($10/мес)", "Business ($18/мес)"],
            },
            "jasper": {
                "auth_type": "Email + Пароль / Google",
                "wallets": "Web (jasper.ai)",
                "how": "Открой jasper.ai, создай аккаунт",
                "subscription_tiers": ["Creator ($49/мес)", "Pro ($125/мес)"],
            },
            "copyai": {
                "auth_type": "Email + Пароль / Google",
                "wallets": "Web (copy.ai)",
                "how": "Открой copy.ai, войди через email или Google",
                "subscription_tiers": ["Free", "Pro ($49/мес)"],
            },
            "writesonic": {
                "auth_type": "Email + Пароль / Google",
                "wallets": "Web (writesonic.com)",
                "how": "Открой writesonic.com, войди через email или Google",
                "subscription_tiers": ["Free", "Pro ($19/мес)"],
            },
            
            # Other
            "character_ai": {
                "auth_type": "Email + Пароль / Google",
                "wallets": "Web (character.ai), Character AI App",
                "how": "Открой character.ai, войди через email/пароль или Google аккаунт",
                "subscription_tiers": ["Free", "Plus ($9.99/мес)"],
            },
            "perplexity": {
                "auth_type": "Email + Пароль / Google / Apple",
                "wallets": "Web (perplexity.ai), Perplexity App",
                "how": "Открой perplexity.ai, войди через email, Google или Apple",
                "subscription_tiers": ["Free", "Pro ($20/мес)"],
            },
            "huggingface": {
                "auth_type": "Логин + Пароль / Google / GitHub",
                "wallets": "Web (huggingface.co)",
                "how": "Открой huggingface.co, войди через логин/пароль, Google или GitHub",
                "subscription_tiers": ["Free", "Pro ($9/мес)"],
            },
            "replicate": {
                "auth_type": "GitHub аккаунт",
                "wallets": "Web (replicate.com)",
                "how": "Открой replicate.com, войди через GitHub аккаунт",
                "subscription_tiers": ["Pay-per-use"],
            },
            "stable_diffusion": {
                "auth_type": "Email + Пароль / Google / GitHub",
                "wallets": "Web (civitai.com), ComfyUI, Automatic1111",
                "how": "Открой civitai.com, войди через email/пароль. Для локального: установи ComfyUI",
            },
            "devin": {
                "auth_type": "Email + Пароль / Google / GitHub",
                "wallets": "Web (app.devin.ai)",
                "how": "Открой app.devin.ai, войди через email, Google или GitHub",
            },
        }

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
        "devin": "Devin AI",
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
                "devin": self._check_devin,
            }.get(detected)

            if handler:
                result = await handler(data, timeout, proxy, session)
                if result.get("exists") and detected in self.auth_info:
                    result["info"]["auth"] = self.auth_info[detected]
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
            "devin": "devin", "devin ai": "devin", "cognition": "devin",
        }
        for keyword, svc in mapping.items():
            if keyword in data_lower:
                return svc
        return None

    async def _check_openai(self, email, timeout, proxy, session):
        result = self.make_result(input=email, service="chatgpt", valid=True)
        if "@" not in email or "." not in email.split("@")[-1]:
            result["info"]["message"] = "Not a valid email format"
            return result
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
        if "@" not in email or "." not in email.split("@")[-1]:
            result["info"]["message"] = "Not a valid email format"
            return result
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
        if "@" not in email or "." not in email.split("@")[-1]:
            result["info"]["message"] = "Not a valid email format"
            return result
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


    async def _check_devin(self, data, timeout, proxy, session):
        result = self.make_result(input=data, service="devin", valid=True)
        clean = data.strip().lstrip("@").replace("https://devin.ai/", "").replace("http://devin.ai/", "")

        if "@" in clean:
            result["info"]["message"] = "Devin AI subscription/account status requires authenticated session"
            result["info"]["subscription_check"] = "requires_login"
            return result

        try:
            profile_url = f"https://devin.ai/{clean}"
            resp = await self.fetch(session, "GET", profile_url, timeout=timeout, proxy=proxy)
            status = resp.status
            text = await resp.text()
            resp.close()

            if status == 200 and "not found" not in text.lower():
                result["exists"] = True
                result["info"]["message"] = "Devin profile/page accessible"
            elif status == 404:
                result["info"]["message"] = "Devin profile not found"
            else:
                result["info"]["message"] = f"HTTP {status}"

            result["info"]["subscription_check"] = "requires_login"
        except Exception as e:
            result["info"]["error"] = str(e)

        return result
    
    # v1.0.81: Интеграция subscription checker
    async def check_with_subscription(self, data: str, credentials: dict = None, 
                                     service: str = None, timeout: int = 10, 
                                     proxy: str = None, session: aiohttp.ClientSession = None) -> dict:
        """
        Проверка аккаунта с информацией о подписке
        
        Args:
            data: email/username для проверки
            credentials: учетные данные для проверки подписки (токены, cookies, etc.)
            service: тип сервиса
            timeout: таймаут
            proxy: прокси
            session: aiohttp сессия
            
        Returns:
            результат с информацией о подписке
        """
        # Базовая проверка аккаунта
        result = await self.check(data, service, timeout, proxy, session)
        
        # Если аккаунт существует и есть credentials - проверяем подписку
        if result.get("exists") and credentials:
            detected_service = result.get("service", service)
            
            own_session = session is None
            if own_session:
                session = aiohttp.ClientSession()
            
            try:
                subscription_info = await global_subscription_checker.check_subscription(
                    detected_service, credentials, session, timeout
                )
                
                # Добавляем информацию о подписке в результат
                result["subscription"] = subscription_info
                
                # Если есть подписка - добавляем в info
                if subscription_info.get("has_subscription"):
                    result["info"]["subscription_tier"] = subscription_info.get("tier", "unknown")
                    result["info"]["subscription_plan"] = subscription_info.get("plan_name", "Unknown")
                    result["info"]["monthly_cost"] = subscription_info.get("monthly_cost", 0.0)
                    
                    # Добавляем features если есть
                    if "features" in subscription_info:
                        result["info"]["features"] = subscription_info["features"]
                    
                    # Добавляем usage если есть
                    if "usage" in subscription_info:
                        result["info"]["usage"] = subscription_info["usage"]
            
            except Exception as e:
                result["subscription"] = {
                    "service": detected_service,
                    "has_subscription": False,
                    "error": str(e)
                }
            
            finally:
                if own_session:
                    await session.close()
        
        return result
    
    # v1.0.81: Валидация API ключей
    async def validate_api_keys(self, api_keys: list, session: aiohttp.ClientSession = None) -> list:
        """
        Проверить список API ключей
        
        Args:
            api_keys: список API ключей для проверки
            session: aiohttp сессия
            
        Returns:
            список результатов валидации
        """
        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession()
        
        try:
            results = await global_api_validator.batch_validate(api_keys, session)
            return results
        
        finally:
            if own_session:
                await session.close()
    
    # v1.0.81: Экспорт аккаунтов с подписками
    def export_accounts(self, results: list, output_format: str = "txt") -> str:
        """
        Экспорт аккаунтов на которые возможна авторизация
        
        Args:
            results: список результатов проверки
            output_format: формат экспорта (txt, json, csv)
            
        Returns:
            путь к файлу экспорта
        """
        # Фильтруем только аккаунты с подписками
        accounts_with_subs = []
        
        for result in results:
            if not isinstance(result, dict):
                continue
            
            # Проверяем наличие подписки
            subscription = result.get("subscription", {})
            if subscription.get("has_subscription"):
                account_info = {
                    "service": result.get("service", "unknown"),
                    "input": result.get("input", ""),
                    "exists": result.get("exists", False),
                    "subscription_tier": subscription.get("tier", "unknown"),
                    "subscription_plan": subscription.get("plan_name", "Unknown"),
                    "monthly_cost": subscription.get("monthly_cost", 0.0),
                    "features": subscription.get("features", []),
                }
                
                # Добавляем usage если есть
                if "usage" in subscription:
                    account_info["usage"] = subscription["usage"]
                
                # Добавляем auth info если есть
                if "auth" in result.get("info", {}):
                    account_info["auth_type"] = result["info"]["auth"].get("auth_type", "")
                    account_info["how_to_login"] = result["info"]["auth"].get("how", "")
                
                accounts_with_subs.append(account_info)
        
        # Создаем директорию exports если не существует
        os.makedirs("exports", exist_ok=True)
        
        # Генерируем имя файла с timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if output_format == "json":
            filename = f"exports/ai_accounts_{timestamp}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(accounts_with_subs, f, indent=2, ensure_ascii=False)
        
        elif output_format == "csv":
            filename = f"exports/ai_accounts_{timestamp}.csv"
            with open(filename, "w", encoding="utf-8", newline="") as f:
                if accounts_with_subs:
                    writer = csv.DictWriter(f, fieldnames=accounts_with_subs[0].keys())
                    writer.writeheader()
                    writer.writerows(accounts_with_subs)
        
        else:  # txt
            filename = f"exports/ai_accounts_{timestamp}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write("AI ACCOUNTS WITH SUBSCRIPTIONS\n")
                f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total accounts: {len(accounts_with_subs)}\n")
                f.write("=" * 80 + "\n\n")
                
                for i, acc in enumerate(accounts_with_subs, 1):
                    f.write(f"[{i}] {acc['service'].upper()}\n")
                    f.write(f"    Account: {acc['input']}\n")
                    f.write(f"    Subscription: {acc['subscription_plan']} (${acc['monthly_cost']}/month)\n")
                    f.write(f"    Tier: {acc['subscription_tier']}\n")
                    
                    if acc.get("features"):
                        f.write(f"    Features: {', '.join(acc['features'])}\n")
                    
                    if acc.get("usage"):
                        f.write(f"    Usage: {acc['usage']}\n")
                    
                    if acc.get("auth_type"):
                        f.write(f"    Auth: {acc['auth_type']}\n")
                    
                    if acc.get("how_to_login"):
                        f.write(f"    How to login: {acc['how_to_login']}\n")
                    
                    f.write("\n" + "-" * 80 + "\n\n")
                
                # Статистика
                f.write("=" * 80 + "\n")
                f.write("STATISTICS\n")
                f.write("=" * 80 + "\n")
                
                # Группируем по сервисам
                services_stats = {}
                total_cost = 0.0
                
                for acc in accounts_with_subs:
                    service = acc["service"]
                    cost = acc["monthly_cost"]
                    
                    if service not in services_stats:
                        services_stats[service] = {"count": 0, "cost": 0.0}
                    
                    services_stats[service]["count"] += 1
                    services_stats[service]["cost"] += cost
                    total_cost += cost
                
                for service, stats in services_stats.items():
                    f.write(f"{service}: {stats['count']} accounts, ${stats['cost']:.2f}/month\n")
                
                f.write(f"\nTotal monthly cost: ${total_cost:.2f}\n")
                f.write(f"Total yearly cost: ${total_cost * 12:.2f}\n")
        
        return filename
