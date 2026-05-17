# -*- coding: utf-8 -*-
"""
AI API Key Validator - Проверка валидности API ключей для AI сервисов
Проверка остатка credits, лимитов, статуса
"""

import asyncio
import aiohttp
import re
from typing import Dict, List, Any, Optional
from datetime import datetime


class AIAPIValidator:
    """Валидатор API ключей для AI сервисов"""
    
    def __init__(self):
        # Паттерны API ключей
        self.api_patterns = {
            "openai": re.compile(r'^sk-(proj-)?[a-zA-Z0-9]{48,}$'),
            "anthropic": re.compile(r'^sk-ant-[a-zA-Z0-9\-]{95,}$'),
            "google": re.compile(r'^AIza[a-zA-Z0-9_\-]{35}$'),
            "replicate": re.compile(r'^r8_[a-zA-Z0-9]{40}$'),
            "huggingface": re.compile(r'^hf_[a-zA-Z0-9]{38}$'),
            "elevenlabs": re.compile(r'^[a-f0-9]{32}$'),
            "stability": re.compile(r'^sk-[a-zA-Z0-9]{48}$'),
            "cohere": re.compile(r'^[a-zA-Z0-9]{40}$'),
            "together": re.compile(r'^[a-f0-9]{64}$'),
        }
    
    def detect_api_key_type(self, api_key: str) -> Optional[str]:
        """
        Определить тип API ключа по паттерну
        
        Args:
            api_key: API ключ
            
        Returns:
            тип сервиса или None
        """
        for service, pattern in self.api_patterns.items():
            if pattern.match(api_key):
                return service
        return None
    
    async def validate_api_key(self, api_key: str, service: Optional[str] = None,
                              session: Optional[aiohttp.ClientSession] = None) -> Dict[str, Any]:
        """
        Проверить валидность API ключа
        
        Args:
            api_key: API ключ для проверки
            service: тип сервиса (опционально, определится автоматически)
            session: aiohttp сессия
            
        Returns:
            информация о ключе
        """
        # Определяем тип ключа
        if not service:
            service = self.detect_api_key_type(api_key)
        
        if not service:
            return {
                "valid": False,
                "service": "unknown",
                "error": "Could not detect API key type"
            }
        
        # Создаем сессию если нужно
        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession()
        
        try:
            # Выбираем обработчик
            handler = {
                "openai": self._validate_openai,
                "anthropic": self._validate_anthropic,
                "google": self._validate_google,
                "replicate": self._validate_replicate,
                "huggingface": self._validate_huggingface,
                "elevenlabs": self._validate_elevenlabs,
                "stability": self._validate_stability,
                "cohere": self._validate_cohere,
                "together": self._validate_together,
            }.get(service)
            
            if handler:
                result = await handler(api_key, session)
            else:
                result = {
                    "valid": False,
                    "service": service,
                    "error": "Service not supported"
                }
        
        finally:
            if own_session:
                await session.close()
        
        return result
    
    async def _validate_openai(self, api_key: str, session: aiohttp.ClientSession) -> Dict:
        """Валидация OpenAI API ключа"""
        result = {
            "service": "OpenAI",
            "valid": False,
            "api_key": api_key[:20] + "..." + api_key[-4:],
            "credits": 0.0,
            "models": [],
            "limits": {},
        }
        
        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            
            # 1. Проверяем валидность через models endpoint
            url = "https://api.openai.com/v1/models"
            resp = await session.get(url, headers=headers, timeout=10)
            
            if resp.status == 200:
                result["valid"] = True
                data = await resp.json()
                result["models"] = [m["id"] for m in data.get("data", [])]
                
                # 2. Проверяем billing/credits
                try:
                    billing_url = "https://api.openai.com/dashboard/billing/credit_grants"
                    billing_resp = await session.get(billing_url, headers=headers, timeout=10)
                    
                    if billing_resp.status == 200:
                        billing_data = await billing_resp.json()
                        
                        # Остаток credits
                        total_granted = billing_data.get("total_granted", 0)
                        total_used = billing_data.get("total_used", 0)
                        total_available = billing_data.get("total_available", 0)
                        
                        result["credits"] = total_available
                        result["credits_used"] = total_used
                        result["credits_granted"] = total_granted
                        
                        # Дата истечения
                        if "grants" in billing_data and billing_data["grants"]:
                            expires_at = billing_data["grants"][0].get("expires_at")
                            if expires_at:
                                result["expires_at"] = datetime.fromtimestamp(expires_at).isoformat()
                
                except:
                    pass
                
                # 3. Проверяем usage/limits
                try:
                    usage_url = "https://api.openai.com/v1/usage"
                    usage_resp = await session.get(usage_url, headers=headers, timeout=10)
                    
                    if usage_resp.status == 200:
                        usage_data = await usage_resp.json()
                        result["usage"] = usage_data
                
                except:
                    pass
            
            elif resp.status == 401:
                result["error"] = "Invalid API key"
            elif resp.status == 429:
                result["valid"] = True
                result["error"] = "Rate limit exceeded (key is valid)"
            else:
                result["error"] = f"HTTP {resp.status}"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def _validate_anthropic(self, api_key: str, session: aiohttp.ClientSession) -> Dict:
        """Валидация Anthropic (Claude) API ключа"""
        result = {
            "service": "Anthropic (Claude)",
            "valid": False,
            "api_key": api_key[:20] + "..." + api_key[-4:],
            "models": [],
        }
        
        try:
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            
            # Проверяем через messages endpoint (минимальный запрос)
            url = "https://api.anthropic.com/v1/messages"
            payload = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "Hi"}]
            }
            
            resp = await session.post(url, headers=headers, json=payload, timeout=10)
            
            if resp.status == 200:
                result["valid"] = True
                result["models"] = [
                    "claude-3-opus-20240229",
                    "claude-3-sonnet-20240229",
                    "claude-3-haiku-20240307",
                    "claude-2.1",
                    "claude-2.0",
                ]
            
            elif resp.status == 401:
                result["error"] = "Invalid API key"
            elif resp.status == 429:
                result["valid"] = True
                result["error"] = "Rate limit exceeded (key is valid)"
            else:
                result["error"] = f"HTTP {resp.status}"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def _validate_google(self, api_key: str, session: aiohttp.ClientSession) -> Dict:
        """Валидация Google AI (Gemini) API ключа"""
        result = {
            "service": "Google AI (Gemini)",
            "valid": False,
            "api_key": api_key[:20] + "..." + api_key[-4:],
            "models": [],
        }
        
        try:
            # Проверяем через models endpoint
            url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"
            resp = await session.get(url, timeout=10)
            
            if resp.status == 200:
                result["valid"] = True
                data = await resp.json()
                result["models"] = [m["name"] for m in data.get("models", [])]
            
            elif resp.status == 400:
                result["error"] = "Invalid API key"
            else:
                result["error"] = f"HTTP {resp.status}"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def _validate_replicate(self, api_key: str, session: aiohttp.ClientSession) -> Dict:
        """Валидация Replicate API ключа"""
        result = {
            "service": "Replicate",
            "valid": False,
            "api_key": api_key[:20] + "..." + api_key[-4:],
        }
        
        try:
            headers = {"Authorization": f"Token {api_key}"}
            
            # Проверяем через account endpoint
            url = "https://api.replicate.com/v1/account"
            resp = await session.get(url, headers=headers, timeout=10)
            
            if resp.status == 200:
                result["valid"] = True
                data = await resp.json()
                
                result["username"] = data.get("username")
                result["type"] = data.get("type")
                
                # Billing info
                if "billing" in data:
                    result["billing"] = data["billing"]
            
            elif resp.status == 401:
                result["error"] = "Invalid API key"
            else:
                result["error"] = f"HTTP {resp.status}"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def _validate_huggingface(self, api_key: str, session: aiohttp.ClientSession) -> Dict:
        """Валидация Hugging Face API ключа"""
        result = {
            "service": "Hugging Face",
            "valid": False,
            "api_key": api_key[:20] + "..." + api_key[-4:],
        }
        
        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            
            # Проверяем через whoami endpoint
            url = "https://huggingface.co/api/whoami-v2"
            resp = await session.get(url, headers=headers, timeout=10)
            
            if resp.status == 200:
                result["valid"] = True
                data = await resp.json()
                
                result["username"] = data.get("name")
                result["fullname"] = data.get("fullname")
                result["email"] = data.get("email")
                result["plan"] = data.get("plan", "free")
                
                # Organizations
                if "orgs" in data:
                    result["organizations"] = [org["name"] for org in data["orgs"]]
            
            elif resp.status == 401:
                result["error"] = "Invalid API key"
            else:
                result["error"] = f"HTTP {resp.status}"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def _validate_elevenlabs(self, api_key: str, session: aiohttp.ClientSession) -> Dict:
        """Валидация ElevenLabs API ключа"""
        result = {
            "service": "ElevenLabs",
            "valid": False,
            "api_key": api_key[:20] + "..." + api_key[-4:],
            "characters": {},
        }
        
        try:
            headers = {"xi-api-key": api_key}
            
            # 1. Проверяем user info
            url = "https://api.elevenlabs.io/v1/user"
            resp = await session.get(url, headers=headers, timeout=10)
            
            if resp.status == 200:
                result["valid"] = True
                data = await resp.json()
                
                # Subscription info
                subscription = data.get("subscription", {})
                result["tier"] = subscription.get("tier", "free")
                result["character_count"] = subscription.get("character_count", 0)
                result["character_limit"] = subscription.get("character_limit", 10000)
                result["characters_remaining"] = max(0, result["character_limit"] - result["character_count"])  # ИСПРАВЛЕНО: не может быть отрицательным
                
                # ИСПРАВЛЕНО: добавлен процент использования
                result["usage_percent"] = round((result["character_count"] / result["character_limit"] * 100), 2) if result["character_limit"] > 0 else 0
                
                # Voice limit
                result["voice_limit"] = subscription.get("voice_limit", 3)
                
                # Next billing
                if "next_character_count_reset_unix" in subscription:
                    reset_time = subscription["next_character_count_reset_unix"]
                    result["next_reset"] = datetime.fromtimestamp(reset_time).isoformat()
                
                # 2. Получаем список голосов
                voices_url = "https://api.elevenlabs.io/v1/voices"
                voices_resp = await session.get(voices_url, headers=headers, timeout=10)
                
                if voices_resp.status == 200:
                    voices_data = await voices_resp.json()
                    result["voices_count"] = len(voices_data.get("voices", []))
            
            elif resp.status == 401:
                result["error"] = "Invalid API key"
            else:
                result["error"] = f"HTTP {resp.status}"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def _validate_stability(self, api_key: str, session: aiohttp.ClientSession) -> Dict:
        """Валидация Stability AI API ключа"""
        result = {
            "service": "Stability AI",
            "valid": False,
            "api_key": api_key[:20] + "..." + api_key[-4:],
            "credits": 0.0,
        }
        
        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            
            # Проверяем balance
            url = "https://api.stability.ai/v1/user/balance"
            resp = await session.get(url, headers=headers, timeout=10)
            
            if resp.status == 200:
                result["valid"] = True
                data = await resp.json()
                
                result["credits"] = data.get("credits", 0)
            
            elif resp.status == 401:
                result["error"] = "Invalid API key"
            else:
                result["error"] = f"HTTP {resp.status}"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def _validate_cohere(self, api_key: str, session: aiohttp.ClientSession) -> Dict:
        """Валидация Cohere API ключа"""
        result = {
            "service": "Cohere",
            "valid": False,
            "api_key": api_key[:20] + "..." + api_key[-4:],
        }
        
        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            
            # Проверяем через check-api-key endpoint
            url = "https://api.cohere.ai/v1/check-api-key"
            resp = await session.post(url, headers=headers, timeout=10)
            
            if resp.status == 200:
                result["valid"] = True
                data = await resp.json()
                
                result["valid_key"] = data.get("valid", False)
            
            elif resp.status == 401:
                result["error"] = "Invalid API key"
            else:
                result["error"] = f"HTTP {resp.status}"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def _validate_together(self, api_key: str, session: aiohttp.ClientSession) -> Dict:
        """Валидация Together AI API ключа"""
        result = {
            "service": "Together AI",
            "valid": False,
            "api_key": api_key[:20] + "..." + api_key[-4:],
        }
        
        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            
            # Проверяем через models endpoint
            url = "https://api.together.xyz/v1/models"
            resp = await session.get(url, headers=headers, timeout=10)
            
            if resp.status == 200:
                result["valid"] = True
                data = await resp.json()
                
                result["models_count"] = len(data)
            
            elif resp.status == 401:
                result["error"] = "Invalid API key"
            else:
                result["error"] = f"HTTP {resp.status}"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def batch_validate(self, api_keys: List[str], 
                            session: Optional[aiohttp.ClientSession] = None) -> List[Dict]:
        """
        Проверить несколько API ключей одновременно
        
        Args:
            api_keys: список API ключей
            session: aiohttp сессия
            
        Returns:
            список результатов
        """
        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession()
        
        try:
            tasks = [self.validate_api_key(key, session=session) for key in api_keys]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Обрабатываем исключения
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append({
                        "valid": False,
                        "service": "unknown",
                        "api_key": api_keys[i][:20] + "...",
                        "error": str(result)
                    })
                else:
                    processed_results.append(result)
            
            return processed_results
        
        finally:
            if own_session:
                await session.close()
    
    def calculate_total_credits(self, validations: List[Dict]) -> Dict[str, Any]:
        """
        Рассчитать общую стоимость всех API ключей
        
        Args:
            validations: список результатов валидации
            
        Returns:
            общая статистика
        """
        # ИСПРАВЛЕНО: валидация входных данных
        if not validations or not isinstance(validations, list):
            return {
                "total_keys": 0,
                "valid_keys": 0,
                "invalid_keys": 0,
                "total_credits": 0.0,
                "total_credits_usd": 0.0,
                "services": {},
            }
        
        total_credits = 0.0
        valid_keys = 0
        invalid_keys = 0
        services = {}
        
        for val in validations:
            if not isinstance(val, dict):  # ИСПРАВЛЕНО: проверка типа
                continue
                
            if val.get("valid"):
                valid_keys += 1
                
                # Суммируем credits
                credits = val.get("credits", 0)
                if isinstance(credits, (int, float)) and credits > 0:  # ИСПРАВЛЕНО: проверка типа
                    total_credits += float(credits)  # ИСПРАВЛЕНО: явное приведение к float
                
                # Группируем по сервисам
                service = val.get("service", "unknown")
                if service not in services:
                    services[service] = {
                        "count": 0,
                        "credits": 0.0
                    }
                
                services[service]["count"] += 1
                if isinstance(credits, (int, float)) and credits > 0:  # ИСПРАВЛЕНО: проверка типа
                    services[service]["credits"] += float(credits)
            else:
                invalid_keys += 1
        
        return {
            "total_keys": len(validations),
            "valid_keys": valid_keys,
            "invalid_keys": invalid_keys,
            "total_credits": round(total_credits, 2),  # ИСПРАВЛЕНО: округление
            "total_credits_usd": round(total_credits, 2),  # ИСПРАВЛЕНО: округление
            "services": services,
        }


# Глобальный экземпляр
global_api_validator = AIAPIValidator()
