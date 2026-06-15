# -*- coding: utf-8 -*-
"""
AI Subscription Checker - Проверка подписок на AI сервисы
Определение активных подписок, tier'ов, стоимости
"""

import asyncio
import aiohttp
import re
import json
from typing import Dict, List, Any, Optional
from datetime import datetime


class AISubscriptionChecker:
    """Проверка подписок на AI сервисы"""
    
    def __init__(self):
        # Цены подписок (USD/месяц)
        self.subscription_prices = {
            # Chat AI
            "chatgpt_plus": 20.0,
            "chatgpt_team": 25.0,
            "chatgpt_enterprise": 60.0,
            "claude_pro": 20.0,
            "gemini_advanced": 19.99,
            "perplexity_pro": 20.0,
            "poe_premium": 19.99,
            
            # Image Generation
            "midjourney_basic": 10.0,
            "midjourney_standard": 30.0,
            "midjourney_pro": 60.0,
            "midjourney_mega": 120.0,
            "leonardo_apprentice": 10.0,
            "leonardo_artisan": 24.0,
            "leonardo_maestro": 48.0,
            "ideogram_plus": 8.0,
            "ideogram_pro": 20.0,
            "playground_pro": 15.0,
            "runway_standard": 12.0,
            "runway_pro": 28.0,
            "runway_unlimited": 76.0,
            
            # Voice AI
            "elevenlabs_starter": 5.0,
            "elevenlabs_creator": 22.0,
            "elevenlabs_pro": 99.0,
            "elevenlabs_scale": 330.0,
            "murf_basic": 19.0,
            "murf_pro": 26.0,
            "playht_creator": 31.20,
            "playht_pro": 79.20,
            
            # Code AI
            "github_copilot": 10.0,
            "github_copilot_business": 19.0,
            "cursor_pro": 20.0,
            "tabnine_pro": 12.0,
            "codeium_pro": 10.0,
            "replit_hacker": 7.0,
            "replit_pro": 20.0,
            
            # Music AI
            "suno_pro": 10.0,
            "suno_premier": 30.0,
            "udio_standard": 10.0,
            "udio_pro": 30.0,
            "mubert_pro": 14.0,
            
            # Productivity
            "notion_plus": 10.0,
            "notion_business": 18.0,
            "jasper_creator": 49.0,
            "jasper_pro": 125.0,
            "copyai_pro": 49.0,
            "writesonic_pro": 19.0,
            
            # Video AI
            "synthesia_starter": 22.0,
            "synthesia_creator": 67.0,
            "heygen_creator": 24.0,
            "heygen_business": 120.0,
            "pika_standard": 10.0,
            "pika_unlimited": 35.0,
        }
        
        # Tier'ы подписок
        self.subscription_tiers = {
            "free": "Free",
            "basic": "Basic",
            "plus": "Plus",
            "pro": "Pro",
            "team": "Team",
            "business": "Business",
            "enterprise": "Enterprise",
            "unlimited": "Unlimited",
        }
    
    async def check_subscription(self, service: str, credentials: Dict[str, str],
                                session: aiohttp.ClientSession, timeout: int = 10) -> Dict[str, Any]:  # ИСПРАВЛЕНО: добавлен timeout
        """
        Проверить подписку на AI сервис
        
        Args:
            service: название сервиса (chatgpt, claude, midjourney, etc.)
            credentials: учетные данные (email, password, token, cookies)
            session: aiohttp сессия
            timeout: таймаут запроса в секундах
            
        Returns:
            информация о подписке
        """
        
        # ИСПРАВЛЕНО: валидация входных данных
        if not service or not isinstance(service, str):
            return {
                "service": "unknown",
                "has_subscription": False,
                "tier": "unknown",
                "error": "Invalid service name"
            }
        
        if not credentials or not isinstance(credentials, dict):
            return {
                "service": service,
                "has_subscription": False,
                "tier": "unknown",
                "error": "Invalid credentials"
            }
        
        handler = {
            "chatgpt": self._check_chatgpt_subscription,
            "claude": self._check_claude_subscription,
            "gemini": self._check_gemini_subscription,
            "midjourney": self._check_midjourney_subscription,
            "elevenlabs": self._check_elevenlabs_subscription,
            "github_copilot": self._check_github_copilot_subscription,
            "leonardo": self._check_leonardo_subscription,
            "runway": self._check_runway_subscription,
            "suno": self._check_suno_subscription,
            "notion": self._check_notion_subscription,
            # NEW
            "huggingface": self._check_huggingface_subscription,
            "perplexity": self._check_perplexity_subscription,
            "cursor": self._check_cursor_subscription,
        }.get(service)
        
        if handler:
            try:
                return await handler(credentials, session)
            except asyncio.TimeoutError:  # ИСПРАВЛЕНО: обработка timeout
                return {
                    "service": service,
                    "has_subscription": False,
                    "tier": "unknown",
                    "error": "Request timeout"
                }
            except Exception as e:  # ИСПРАВЛЕНО: обработка всех исключений
                return {
                    "service": service,
                    "has_subscription": False,
                    "tier": "unknown",
                    "error": f"Unexpected error: {str(e)}"
                }
        
        return {
            "service": service,
            "has_subscription": False,
            "tier": "unknown",
            "error": "Service not supported"
        }
    
    async def _check_chatgpt_subscription(self, credentials: Dict, session: aiohttp.ClientSession) -> Dict:
        """Проверка подписки ChatGPT"""
        result = {
            "service": "ChatGPT",
            "has_subscription": False,
            "tier": "free",
            "plan_name": "Free",
            "monthly_cost": 0.0,
            "features": [],
            "limits": {},
        }
        
        try:
            # Если есть access token
            if "access_token" in credentials:
                headers = {"Authorization": f"Bearer {credentials['access_token']}"}
                
                # Проверяем subscription через API
                url = "https://api.openai.com/v1/dashboard/billing/subscription"
                resp = await session.get(url, headers=headers, timeout=10)
                
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Определяем tier
                    plan = data.get("plan", {})
                    plan_id = plan.get("id", "free")
                    
                    if "plus" in plan_id.lower():
                        result["has_subscription"] = True
                        result["tier"] = "plus"
                        result["plan_name"] = "ChatGPT Plus"
                        result["monthly_cost"] = 20.0
                        result["features"] = [
                            "GPT-4 access",
                            "Faster response times",
                            "Priority access",
                            "DALL-E 3 access",
                            "Advanced Data Analysis",
                        ]
                        result["limits"] = {
                            "gpt4_messages": "40 messages / 3 hours",
                            "dalle_generations": "50 / day",
                        }
                    
                    elif "team" in plan_id.lower():
                        result["has_subscription"] = True
                        result["tier"] = "team"
                        result["plan_name"] = "ChatGPT Team"
                        result["monthly_cost"] = 25.0
                        result["features"] = [
                            "All Plus features",
                            "Team workspace",
                            "Admin console",
                            "Higher message caps",
                        ]
                    
                    elif "enterprise" in plan_id.lower():
                        result["has_subscription"] = True
                        result["tier"] = "enterprise"
                        result["plan_name"] = "ChatGPT Enterprise"
                        result["monthly_cost"] = 60.0
                        result["features"] = [
                            "Unlimited GPT-4",
                            "Extended context",
                            "Admin controls",
                            "SSO",
                            "Data privacy",
                        ]
                    
                    # Дата следующего платежа
                    if "next_billing_date" in data:
                        result["next_billing"] = data["next_billing_date"]
                    
                    # Использование
                    if "usage" in data:
                        result["usage"] = data["usage"]
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def _check_claude_subscription(self, credentials: Dict, session: aiohttp.ClientSession) -> Dict:
        """Проверка подписки Claude"""
        result = {
            "service": "Claude",
            "has_subscription": False,
            "tier": "free",
            "plan_name": "Free",
            "monthly_cost": 0.0,
            "features": [],
        }
        
        try:
            if "session_key" in credentials:
                headers = {"Cookie": f"sessionKey={credentials['session_key']}"}
                
                url = "https://claude.ai/api/organizations"
                resp = await session.get(url, headers=headers, timeout=10)
                
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Проверяем подписку
                    for org in data:
                        capabilities = org.get("capabilities", [])
                        
                        if "claude_pro" in capabilities:
                            result["has_subscription"] = True
                            result["tier"] = "pro"
                            result["plan_name"] = "Claude Pro"
                            result["monthly_cost"] = 20.0
                            result["features"] = [
                                "5x more usage",
                                "Priority access",
                                "Early access to new features",
                            ]
                            result["limits"] = {
                                "messages": "5x more than free tier"
                            }
                            break
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def _check_midjourney_subscription(self, credentials: Dict, session: aiohttp.ClientSession) -> Dict:
        """Проверка подписки Midjourney"""
        result = {
            "service": "Midjourney",
            "has_subscription": False,
            "tier": "free",
            "plan_name": "Free Trial",
            "monthly_cost": 0.0,
            "features": [],
            "limits": {},
        }
        
        try:
            if "discord_token" in credentials:
                headers = {"Authorization": credentials["discord_token"]}
                
                # Проверяем через Discord API
                url = "https://discord.com/api/v10/users/@me/billing/subscriptions"
                resp = await session.get(url, headers=headers, timeout=10)
                
                if resp.status == 200:
                    subs = await resp.json()
                    
                    # Ищем подписку Midjourney
                    for sub in subs:
                        if "midjourney" in sub.get("application_id", "").lower():
                            plan_id = sub.get("plan_id", "")
                            
                            # Определяем tier
                            if "basic" in plan_id.lower():
                                result["has_subscription"] = True
                                result["tier"] = "basic"
                                result["plan_name"] = "Basic Plan"
                                result["monthly_cost"] = 10.0
                                result["features"] = ["3.3 hrs fast GPU time", "Unlimited relaxed"]
                                result["limits"] = {"fast_hours": "3.3 hrs/month"}
                            
                            elif "standard" in plan_id.lower():
                                result["has_subscription"] = True
                                result["tier"] = "standard"
                                result["plan_name"] = "Standard Plan"
                                result["monthly_cost"] = 30.0
                                result["features"] = ["15 hrs fast GPU time", "Unlimited relaxed"]
                                result["limits"] = {"fast_hours": "15 hrs/month"}
                            
                            elif "pro" in plan_id.lower():
                                result["has_subscription"] = True
                                result["tier"] = "pro"
                                result["plan_name"] = "Pro Plan"
                                result["monthly_cost"] = 60.0
                                result["features"] = ["30 hrs fast GPU time", "Stealth mode"]
                                result["limits"] = {"fast_hours": "30 hrs/month"}
                            
                            elif "mega" in plan_id.lower():
                                result["has_subscription"] = True
                                result["tier"] = "mega"
                                result["plan_name"] = "Mega Plan"
                                result["monthly_cost"] = 120.0
                                result["features"] = ["60 hrs fast GPU time", "Stealth mode"]
                                result["limits"] = {"fast_hours": "60 hrs/month"}
                            
                            # Дата следующего платежа
                            if "current_period_end" in sub:
                                result["next_billing"] = sub["current_period_end"]
                            
                            break
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def _check_elevenlabs_subscription(self, credentials: Dict, session: aiohttp.ClientSession) -> Dict:
        """Проверка подписки ElevenLabs"""
        result = {
            "service": "ElevenLabs",
            "has_subscription": False,
            "tier": "free",
            "plan_name": "Free",
            "monthly_cost": 0.0,
            "features": [],
            "limits": {},
        }
        
        try:
            if "api_key" in credentials:
                headers = {"xi-api-key": credentials["api_key"]}
                
                # Проверяем subscription
                url = "https://api.elevenlabs.io/v1/user/subscription"
                resp = await session.get(url, headers=headers, timeout=10)
                
                if resp.status == 200:
                    data = await resp.json()
                    
                    tier = data.get("tier", "free").lower()
                    
                    if tier == "starter":
                        result["has_subscription"] = True
                        result["tier"] = "starter"
                        result["plan_name"] = "Starter"
                        result["monthly_cost"] = 5.0
                        result["features"] = ["30,000 characters/month", "3 custom voices"]
                        result["limits"] = {
                            "characters": "30,000/month",
                            "custom_voices": 3
                        }
                    
                    elif tier == "creator":
                        result["has_subscription"] = True
                        result["tier"] = "creator"
                        result["plan_name"] = "Creator"
                        result["monthly_cost"] = 22.0
                        result["features"] = ["100,000 characters/month", "30 custom voices"]
                        result["limits"] = {
                            "characters": "100,000/month",
                            "custom_voices": 30
                        }
                    
                    elif tier == "pro":
                        result["has_subscription"] = True
                        result["tier"] = "pro"
                        result["plan_name"] = "Pro"
                        result["monthly_cost"] = 99.0
                        result["features"] = ["500,000 characters/month", "160 custom voices"]
                        result["limits"] = {
                            "characters": "500,000/month",
                            "custom_voices": 160
                        }
                    
                    # Использование
                    character_count = data.get("character_count", 0)
                    character_limit = data.get("character_limit", 10000)
                    
                    result["usage"] = {
                        "characters_used": character_count,
                        "characters_limit": character_limit,
                        "characters_remaining": max(0, character_limit - character_count),  # ИСПРАВЛЕНО: не может быть отрицательным
                        "usage_percent": round((character_count / character_limit * 100), 2) if character_limit > 0 else 0  # ИСПРАВЛЕНО: округление
                    }
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def _check_github_copilot_subscription(self, credentials: Dict, session: aiohttp.ClientSession) -> Dict:
        """Проверка подписки GitHub Copilot"""
        result = {
            "service": "GitHub Copilot",
            "has_subscription": False,
            "tier": "free",
            "plan_name": "Free",
            "monthly_cost": 0.0,
            "features": [],
        }
        
        try:
            if "github_token" in credentials:
                headers = {"Authorization": f"token {credentials['github_token']}"}
                
                # Проверяем Copilot subscription
                url = "https://api.github.com/user/copilot_seat_details"
                resp = await session.get(url, headers=headers, timeout=10)
                
                if resp.status == 200:
                    data = await resp.json()
                    
                    if data.get("seat", {}).get("created_at"):
                        result["has_subscription"] = True
                        result["tier"] = "individual"
                        result["plan_name"] = "GitHub Copilot Individual"
                        result["monthly_cost"] = 10.0
                        result["features"] = [
                            "Code completions",
                            "Chat in IDE",
                            "CLI assistance",
                            "Mobile support",
                        ]
                        
                        # Проверяем business tier
                        if data.get("seat", {}).get("organization"):
                            result["tier"] = "business"
                            result["plan_name"] = "GitHub Copilot Business"
                            result["monthly_cost"] = 19.0
                            result["features"].extend([
                                "Organization-wide policies",
                                "IP indemnity",
                                "Enterprise support",
                            ])
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def _check_leonardo_subscription(self, credentials: Dict, session: aiohttp.ClientSession) -> Dict:
        """Проверка подписки Leonardo.AI"""
        result = {
            "service": "Leonardo.AI",
            "has_subscription": False,
            "tier": "free",
            "plan_name": "Free",
            "monthly_cost": 0.0,
            "features": [],
            "limits": {},
        }
        
        try:
            if "auth_token" in credentials:
                headers = {"Authorization": f"Bearer {credentials['auth_token']}"}
                
                url = "https://cloud.leonardo.ai/api/rest/v1/me"
                resp = await session.get(url, headers=headers, timeout=10)
                
                if resp.status == 200:
                    data = await resp.json()
                    user = data.get("user_details", [{}])[0]
                    
                    subscription = user.get("subscriptionModelTokens", 0)
                    
                    # ИСПРАВЛЕНО: порядок проверки должен быть от большего к меньшему
                    if subscription >= 60000:
                        result["has_subscription"] = True
                        result["tier"] = "maestro"
                        result["plan_name"] = "Maestro"
                        result["monthly_cost"] = 48.0
                        result["limits"] = {"tokens": "60,000/month"}
                    
                    elif subscription >= 25000:
                        result["has_subscription"] = True
                        result["tier"] = "artisan"
                        result["plan_name"] = "Artisan"
                        result["monthly_cost"] = 24.0
                        result["limits"] = {"tokens": "25,000/month"}
                    
                    elif subscription >= 8500:
                        result["has_subscription"] = True
                        result["tier"] = "apprentice"
                        result["plan_name"] = "Apprentice"
                        result["monthly_cost"] = 10.0
                        result["limits"] = {"tokens": "8,500/month"}
                    
                    # Использование
                    tokens_used = user.get("subscriptionTokens", 0)
                    tokens_limit = subscription  # ИСПРАВЛЕНО: используем subscription как лимит
                    result["usage"] = {
                        "tokens_used": tokens_used,
                        "tokens_limit": tokens_limit,
                        "tokens_remaining": max(0, tokens_limit - tokens_used)  # ИСПРАВЛЕНО: не может быть отрицательным
                    }
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def _check_runway_subscription(self, credentials: Dict, session: aiohttp.ClientSession) -> Dict:
        """Проверка подписки Runway"""
        result = {
            "service": "Runway",
            "has_subscription": False,
            "tier": "free",
            "plan_name": "Free",
            "monthly_cost": 0.0,
            "features": [],
        }
        
        # Runway требует авторизации через их API
        # Здесь базовая структура
        result["note"] = "Requires authenticated session"
        
        return result
    
    async def _check_suno_subscription(self, credentials: Dict, session: aiohttp.ClientSession) -> Dict:
        """Проверка подписки Suno AI"""
        result = {
            "service": "Suno AI",
            "has_subscription": False,
            "tier": "free",
            "plan_name": "Free",
            "monthly_cost": 0.0,
            "features": [],
            "limits": {},
        }
        
        try:
            if "session_id" in credentials:
                cookies = {"__session": credentials["session_id"]}
                
                url = "https://studio-api.suno.ai/api/billing/info"
                resp = await session.get(url, cookies=cookies, timeout=10)
                
                if resp.status == 200:
                    data = await resp.json()
                    
                    plan = data.get("tier", "free").lower()
                    
                    if plan == "pro":
                        result["has_subscription"] = True
                        result["tier"] = "pro"
                        result["plan_name"] = "Pro"
                        result["monthly_cost"] = 10.0
                        result["features"] = ["500 credits/month", "Priority queue"]
                        result["limits"] = {"credits": "500/month"}
                    
                    elif plan == "premier":
                        result["has_subscription"] = True
                        result["tier"] = "premier"
                        result["plan_name"] = "Premier"
                        result["monthly_cost"] = 30.0
                        result["features"] = ["2000 credits/month", "Fastest queue"]
                        result["limits"] = {"credits": "2000/month"}
                    
                    # Использование
                    credits_used = data.get("monthly_usage", 0)
                    credits_limit = data.get("monthly_limit", 50)
                    
                    result["usage"] = {
                        "credits_used": credits_used,
                        "credits_limit": credits_limit,
                        "credits_remaining": max(0, credits_limit - credits_used),  # ИСПРАВЛЕНО: не может быть отрицательным
                        "usage_percent": round((credits_used / credits_limit * 100), 2) if credits_limit > 0 else 0  # ИСПРАВЛЕНО: округление
                    }
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def _check_gemini_subscription(self, credentials: Dict, session: aiohttp.ClientSession) -> Dict:
        """Проверка подписки Google Gemini"""
        result = {
            "service": "Google Gemini",
            "has_subscription": False,
            "tier": "free",
            "plan_name": "Free",
            "monthly_cost": 0.0,
            "features": [],
        }
        
        # Gemini требует Google OAuth
        result["note"] = "Requires Google OAuth authentication"
        
        return result
    
    async def _check_notion_subscription(self, credentials: Dict, session: aiohttp.ClientSession) -> Dict:
        """Проверка подписки Notion"""
        result = {
            "service": "Notion",
            "has_subscription": False,
            "tier": "free",
            "plan_name": "Free",
            "monthly_cost": 0.0,
            "features": [],
        }
        
        # Notion требует OAuth или internal integration
        result["note"] = "Requires Notion API key or OAuth"
        
        return result
    
    def calculate_total_value(self, subscriptions: List[Dict]) -> Dict[str, Any]:
        """
        Рассчитать общую стоимость всех подписок
        
        Args:
            subscriptions: список подписок
            
        Returns:
            общая статистика
        """
        # ИСПРАВЛЕНО: валидация входных данных
        if not subscriptions or not isinstance(subscriptions, list):
            return {
                "active_subscriptions": 0,
                "total_monthly": 0.0,
                "total_yearly": 0.0,
                "services": [],
                "estimated_value": 0.0,
            }
        
        total_monthly = 0.0
        total_yearly = 0.0
        active_count = 0
        services = []
        
        for sub in subscriptions:
            if not isinstance(sub, dict):  # ИСПРАВЛЕНО: проверка типа
                continue
                
            if sub.get("has_subscription"):
                active_count += 1
                monthly_cost = sub.get("monthly_cost", 0.0)
                
                # ИСПРАВЛЕНО: проверка типа и валидация
                if isinstance(monthly_cost, (int, float)) and monthly_cost > 0:
                    total_monthly += float(monthly_cost)
                    total_yearly += float(monthly_cost) * 12
                    
                    services.append({
                        "service": sub.get("service", "Unknown"),
                        "plan": sub.get("plan_name", "Unknown"),
                        "cost": float(monthly_cost)
                    })
        
        return {
            "active_subscriptions": active_count,
            "total_monthly": round(total_monthly, 2),  # ИСПРАВЛЕНО: округление
            "total_yearly": round(total_yearly, 2),  # ИСПРАВЛЕНО: округление
            "services": services,
            "estimated_value": round(total_monthly * 6, 2),  # ИСПРАВЛЕНО: округление
        }


    async def _check_huggingface_subscription(self, credentials: Dict, session: aiohttp.ClientSession) -> Dict:
        """Проверка подписки Hugging Face"""
        result = {
            "service": "Hugging Face",
            "has_subscription": False,
            "tier": "free",
            "plan_name": "Free",
            "monthly_cost": 0.0,
            "features": [],
        }
        try:
            api_key = credentials.get("api_key", "")
            if not api_key:
                result["error"] = "No API key provided"
                return result

            headers = {"Authorization": f"Bearer {api_key}"}
            resp = await session.get("https://huggingface.co/api/whoami",
                                     headers=headers, timeout=10)
            if resp.status == 200:
                data = await resp.json()
                resp.close()

                is_pro = data.get("isPro", False)
                if is_pro:
                    result["has_subscription"] = True
                    result["tier"] = "pro"
                    result["plan_name"] = "Pro"
                    result["monthly_cost"] = 9.0
                    result["features"] = [
                        "PRO badge",
                        "ZeroGPU access (Shared GPU)",
                        "Extended Inference API limits",
                        "Priority support",
                    ]
                # Дополнительно — показываем username и организации
                result["username"] = data.get("name", "")
                result["email"] = data.get("email", "")
                orgs = data.get("orgs", [])
                if orgs:
                    result["organizations"] = [o.get("name", "") for o in orgs]
            elif resp.status == 401:
                resp.close()
                result["error"] = "Invalid token"
            else:
                resp.close()
                result["error"] = f"HTTP {resp.status}"
        except Exception as e:
            result["error"] = str(e)
        return result

    async def _check_perplexity_subscription(self, credentials: Dict, session: aiohttp.ClientSession) -> Dict:
        """Проверка подписки Perplexity AI"""
        result = {
            "service": "Perplexity AI",
            "has_subscription": False,
            "tier": "free",
            "plan_name": "Free",
            "monthly_cost": 0.0,
            "features": [],
        }
        # Perplexity Pro требует авторизации через их сайт — нет публичного API
        result["note"] = "Requires authenticated browser session"
        return result

    async def _check_cursor_subscription(self, credentials: Dict, session: aiohttp.ClientSession) -> Dict:
        """Проверка подписки Cursor IDE"""
        result = {
            "service": "Cursor",
            "has_subscription": False,
            "tier": "free",
            "plan_name": "Free",
            "monthly_cost": 0.0,
            "features": [],
        }
        result["note"] = "Requires Cursor account session"
        return result


# Глобальный экземпляр
global_subscription_checker = AISubscriptionChecker()
