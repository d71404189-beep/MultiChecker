import asyncio
import aiohttp
import re

class AIChecker:
    def __init__(self):
        self.services = {
            "chatgpt": {
                "name": "ChatGPT/OpenAI",
                "check_type": "email",
                "api_endpoint": "https://api.openai.com/v1"
            },
            "gemini": {
                "name": "Google Gemini",
                "check_type": "email",
                "api_endpoint": "https://generativelanguage.googleapis.com"
            },
            "claude": {
                "name": "Claude/Anthropic",
                "check_type": "email",
                "api_endpoint": "https://api.anthropic.com"
            },
            "midjourney": {
                "name": "Midjourney",
                "check_type": "discord",
                "api_endpoint": None
            },
            "stable_diffusion": {
                "name": "Stable Diffusion",
                "check_type": "email",
                "api_endpoint": None
            },
            "character_ai": {
                "name": "Character AI",
                "check_type": "email",
                "api_endpoint": None
            },
            "perplexity": {
                "name": "Perplexity AI",
                "check_type": "email",
                "api_endpoint": None
            },
            "cohere": {
                "name": "Cohere",
                "check_type": "email",
                "api_endpoint": None
            },
            "huggingface": {
                "name": "Hugging Face",
                "check_type": "email",
                "api_endpoint": None
            },
            "replicate": {
                "name": "Replicate",
                "check_type": "email",
                "api_endpoint": None
            },
        }
    
    async def check(self, data: str, service: str = None, timeout: int = 10) -> dict:
        result = {
            "input": data,
            "service": service or "unknown",
            "valid": False,
            "exists": False,
            "info": {}
        }
        
        if "@" in data:
            detected = service or "chatgpt"
        else:
            detected = self._detect_service(data) or service or "chatgpt"
        
        result["service"] = detected
        
        if detected == "chatgpt":
            result = await self._check_openai(data, timeout)
        elif detected == "gemini":
            result = await self._check_gemini(data, timeout)
        elif detected == "claude":
            result = await self._check_claude(data, timeout)
        elif detected == "midjourney":
            result = await self._check_midjourney(data, timeout)
        elif detected == "character_ai":
            result = await self._check_character_ai(data, timeout)
        elif detected == "perplexity":
            result = await self._check_perplexity(data, timeout)
        elif detected == "huggingface":
            result = await self._check_huggingface(data, timeout)
        
        return result
    
    def _detect_service(self, data: str) -> str:
        data_lower = data.lower()
        
        if "openai" in data_lower or "chatgpt" in data_lower:
            return "chatgpt"
        elif "google" in data_lower or "gemini" in data_lower:
            return "gemini"
        elif "claude" in data_lower or "anthropic" in data_lower:
            return "claude"
        elif "midjourney" in data_lower:
            return "midjourney"
        
        return None
    
    async def _check_openai(self, email: str, timeout: int) -> dict:
        result = {"input": email, "service": "chatgpt", "valid": True, "exists": False, "info": {}}
        
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://api.openai.com/v1/auth/signup"
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0"
                }
                payload = {"email": email}
                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    data = await resp.json()
                    
                    if resp.status == 200:
                        if data.get("existing_user") == True:
                            result["exists"] = True
                            result["info"]["message"] = "Account exists"
                        elif data.get("message") == "Email already exists":
                            result["exists"] = True
                            result["info"]["message"] = "Email already registered"
                        elif data.get("message") == "We were unable to verify your email":
                            result["info"]["message"] = "Email verification failed"
                        else:
                            result["info"]["message"] = data.get("message", "Unknown response")
                    elif resp.status == 400:
                        if "already exists" in str(data).lower():
                            result["exists"] = True
                            result["info"]["message"] = "Email already registered"
                        else:
                            result["info"]["message"] = data.get("error", {}).get("message", "Invalid request")
        except asyncio.TimeoutError:
            result["info"]["error"] = "Timeout"
        except Exception as e:
            result["info"]["error"] = str(e)
        
        return result
    
    async def _check_gemini(self, email: str, timeout: int) -> dict:
        result = {"input": email, "service": "gemini", "valid": True, "exists": False, "info": {}}
        
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://accounts.google.com/signup/v1/createaccount"
                params = {"email": email, "flowName": "GlifWebSignIn"}
                headers = {"User-Agent": "Mozilla/5.0"}
                async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    result["info"]["status"] = resp.status
        except Exception as e:
            result["info"]["error"] = str(e)
        
        return result
    
    async def _check_claude(self, email: str, timeout: int) -> dict:
        result = {"input": email, "service": "claude", "valid": True, "exists": False, "info": {}}
        
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://api.anthropic.com/v1/auth/signup"
                headers = {
                    "Content-Type": "application/json",
                    "x-api-key": "sk-ant-api03-placeholder",
                    "User-Agent": "Mozilla/5.0"
                }
                payload = {"email": email}
                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    data = await resp.json()
                    result["info"]["response"] = data
        except Exception as e:
            result["info"]["error"] = str(e)
        
        return result
    
    async def _check_midjourney(self, username: str, timeout: int) -> dict:
        result = {"input": username, "service": "midjourney", "valid": True, "exists": False, "info": {}}
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://discord.com/api/v9/users/@me"
                headers = {"User-Agent": "Mozilla/5.0"}
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    result["info"]["status"] = resp.status
        except Exception as e:
            result["info"]["error"] = str(e)
        
        return result
    
    async def _check_character_ai(self, username: str, timeout: int) -> dict:
        result = {"input": username, "service": "character_ai", "valid": True, "exists": False, "info": {}}
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://character.ai/favicon.ico"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    result["info"]["status"] = resp.status
                    result["exists"] = True
        except Exception as e:
            result["info"]["error"] = str(e)
        
        return result
    
    async def _check_perplexity(self, email: str, timeout: int) -> dict:
        result = {"input": email, "service": "perplexity", "valid": True, "exists": False, "info": {}}
        return result
    
    async def _check_huggingface(self, username: str, timeout: int) -> dict:
        result = {"input": username, "service": "huggingface", "valid": True, "exists": False, "info": {}}
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://huggingface.co/{username}"
                headers = {"User-Agent": "Mozilla/5.0"}
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout), headers=headers) as resp:
                    result["info"]["status"] = resp.status
                    if resp.status == 200:
                        result["exists"] = True
                        result["info"]["message"] = "Profile exists"
                    elif resp.status == 404:
                        result["info"]["message"] = "Profile not found"
        except Exception as e:
            result["info"]["error"] = str(e)
        
        return result
