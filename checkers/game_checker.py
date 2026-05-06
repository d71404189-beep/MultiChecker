import asyncio
import aiohttp
import re
import json

class GameChecker:
    def __init__(self):
        self.games = {
            "steam": {"name": "Steam", "pattern": r'^7656119[0-9]{10}$'},
            "epic": {"name": "Epic Games", "pattern": r'^[a-zA-Z0-9_-]{1,}$'},
            "rockstar": {"name": "Rockstar Games", "pattern": r'^[a-zA-Z0-9_-]{3,20}$'},
            "origin": {"name": "EA Origin", "pattern": r'^[a-zA-Z0-9_-]{3,20}$'},
            "ubisoft": {"name": "Ubisoft", "pattern": r'^[a-zA-Z0-9_-]{3,20}$'},
            "riot": {"name": "Riot Games", "pattern": r'^.{2,16}$'},
            "blizzard": {"name": "Blizzard", "pattern": r'^.{2,20}$'},
            "xbox": {"name": "Xbox", "pattern": r'^[a-zA-Z0-9_-]{1,}$'},
            "playstation": {"name": "PlayStation", "pattern": r'^[a-zA-Z0-9_-]{1,}$'},
            "nintendo": {"name": "Nintendo", "pattern": r'^[a-zA-Z0-9_-]{1,}$'},
        }
    
    async def check(self, data: str, platform: str = None, timeout: int = 10) -> dict:
        result = {
            "input": data,
            "platform": platform or "unknown",
            "valid": False,
            "exists": False,
            "info": {}
        }
        
        detected = platform or self._detect_platform(data)
        result["platform"] = detected
        
        if detected == "steam":
            result = await self._check_steam(data, timeout)
        elif detected == "epic":
            result = await self._check_epic(data, timeout)
        elif detected == "rockstar":
            result = await self._check_rockstar(data, timeout)
        elif detected == "origin":
            result = await self._check_origin(data, timeout)
        elif detected == "ubisoft":
            result = await self._check_ubisoft(data, timeout)
        elif detected == "riot":
            result = await self._check_riot(data, timeout)
        elif detected == "blizzard":
            result = await self._check_blizzard(data, timeout)
        
        return result
    
    def _detect_platform(self, data: str) -> str:
        data = data.strip()
        
        if re.match(r'^7656119[0-9]{10}$', data):
            return "steam"
        
        if re.match(r'^[a-zA-Z0-9_-]{3,16}$', data):
            return "epic"
        
        return "epic"
    
    async def _check_steam(self, steam_id: str, timeout: int) -> dict:
        result = {"input": steam_id, "platform": "steam", "valid": True, "exists": False, "info": {}}
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key=STEAM_API_KEY&steamids={steam_id}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("response", {}).get("players"):
                            player = data["response"]["players"][0]
                            result["exists"] = True
                            result["info"]["personaname"] = player.get("personaname", "")
                            result["info"]["profileurl"] = player.get("profileurl", "")
                            result["info"]["personastate"] = player.get("personastate", 0)
        except Exception as e:
            result["info"]["error"] = str(e)
        
        return result
    
    async def _check_epic(self, username: str, timeout: int) -> dict:
        result = {"input": username, "platform": "epic", "valid": True, "exists": False, "info": {}}
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://account-public-service-prod.ol.epicgames.com/accountService/api/public/account/byDisplayName/{username}"
                headers = {"User-Agent": "EpicGamesLauncher/12.2.1-2171"}
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout), headers=headers) as resp:
                    result["info"]["status"] = resp.status
                    if resp.status == 200:
                        data = await resp.json()
                        result["exists"] = True
                        result["info"]["accountId"] = data.get("id", "")
        except Exception as e:
            result["info"]["error"] = str(e)
        
        return result
    
    async def _check_rockstar(self, username: str, timeout: int) -> dict:
        result = {"input": username, "platform": "rockstar", "valid": True, "exists": False, "info": {}}
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://www.rockstargames.com/nr/i/v1/profile/{username}"
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout), headers=headers) as resp:
                    result["info"]["status"] = resp.status
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("isAvailable") == True:
                            result["exists"] = False
                        else:
                            result["exists"] = True
        except Exception as e:
            result["info"]["error"] = str(e)
        
        return result
    
    async def _check_origin(self, username: str, timeout: int) -> dict:
        result = {"input": username, "platform": "origin", "valid": True, "exists": False, "info": {}}
        return result
    
    async def _check_ubisoft(self, username: str, timeout: int) -> dict:
        result = {"input": username, "platform": "ubisoft", "valid": True, "exists": False, "info": {}}
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://public-ubiservices.ubi.com/v3/profiles?namesOnPlatform={username}"
                headers = {"Ubi-AppId": "00000000-0000-0000-0000-000000000000", "User-Agent": "Mozilla/5.0"}
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout), headers=headers) as resp:
                    result["info"]["status"] = resp.status
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("profiles"):
                            result["exists"] = True
        except Exception as e:
            result["info"]["error"] = str(e)
        
        return result
    
    async def _check_riot(self, username: str, timeout: int) -> dict:
        result = {"input": username, "platform": "riot", "valid": True, "exists": False, "info": {}}
        
        username_parts = username.split("#")
        if len(username_parts) == 2:
            riot_id = username_parts[0]
            tag = username_parts[1]
            
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"https://api.riotgames.com/riot/account/v1/accounts/by-riot-id/{riot_id}/{tag}"
                    headers = {"User-Agent": "Mozilla/5.0"}
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout), headers=headers) as resp:
                        result["info"]["status"] = resp.status
                        if resp.status == 200:
                            data = await resp.json()
                            result["exists"] = True
                            result["info"]["puuid"] = data.get("puuid", "")
                            result["info"]["game_name"] = data.get("gameName", "")
            except Exception as e:
                result["info"]["error"] = str(e)
        
        return result
    
    async def _check_blizzard(self, username: str, timeout: int) -> dict:
        result = {"input": username, "platform": "blizzard", "valid": True, "exists": False, "info": {}}
        return result
