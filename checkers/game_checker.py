import asyncio
import aiohttp
import re

from checkers.base_checker import BaseChecker


class GameChecker(BaseChecker):
    def __init__(self):
        self.games = {
            "steam": {"name": "Steam", "pattern": r'^7656119[0-9]{10}$'},
            "epic": {"name": "Epic Games", "pattern": r'^[a-zA-Z0-9_-]{3,}$'},
            "rockstar": {"name": "Rockstar Games", "pattern": r'^[a-zA-Z0-9_-]{3,20}$'},
            "origin": {"name": "EA Origin", "pattern": r'^[a-zA-Z0-9_-]{3,20}$'},
            "ubisoft": {"name": "Ubisoft", "pattern": r'^[a-zA-Z0-9_-]{3,20}$'},
            "riot": {"name": "Riot Games", "pattern": r'^.{2,16}#.{2,5}$'},
            "blizzard": {"name": "Blizzard", "pattern": r'^.{2,20}#[0-9]{4,6}$'},
            "xbox": {"name": "Xbox", "pattern": r'^[a-zA-Z0-9_ -]{1,15}$'},
            "playstation": {"name": "PlayStation", "pattern": r'^[a-zA-Z0-9_-]{3,16}$'},
        }

    async def check(self, data: str, platform: str = None, timeout: int = 10, proxy: str = None, session: aiohttp.ClientSession = None) -> dict:
        result = self.make_result(input=data, platform=platform or "unknown")

        detected = platform or self._detect_platform(data)
        result["platform"] = detected

        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession()

        try:
            handler = {
                "steam": self._check_steam,
                "epic": self._check_epic,
                "rockstar": self._check_rockstar,
                "origin": self._check_origin,
                "ubisoft": self._check_ubisoft,
                "riot": self._check_riot,
                "blizzard": self._check_blizzard,
                "xbox": self._check_xbox,
                "playstation": self._check_playstation,
            }.get(detected)

            if handler:
                result = await handler(data, timeout, proxy, session)
            else:
                result["info"]["error"] = f"No checker for {detected}"
        finally:
            if own_session:
                await session.close()

        return result

    def _detect_platform(self, data: str) -> str:
        data = data.strip()

        if re.match(r'^7656119[0-9]{10}$', data):
            return "steam"

        if "#" in data:
            parts = data.split("#")
            if len(parts) == 2 and parts[1].isdigit():
                return "blizzard" if len(parts[1]) >= 4 else "riot"
            return "riot"

        if re.match(r'^https?://steamcommunity\.com', data):
            return "steam"

        if re.match(r'^[a-zA-Z0-9_-]{3,16}$', data):
            return "steam"

        return "steam"

    async def _check_steam(self, steam_id, timeout, proxy, session):
        result = self.make_result(input=steam_id, platform="steam", valid=True)
        clean = steam_id.strip()
        if "steamcommunity.com" in clean:
            parts = clean.rstrip("/").split("/")
            clean = parts[-1]

        if re.match(r'^7656119[0-9]{10}$', clean):
            try:
                url = f"https://steamcommunity.com/profiles/{clean}/?xml=1"
                resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
                text = await resp.text()
                resp.close()
                if "<steamID>" in text:
                    result["exists"] = True
                    name_match = re.search(r'<steamID><!\[CDATA\[(.*?)\]\]></steamID>', text)
                    if name_match:
                        result["info"]["personaname"] = name_match.group(1)
                    result["info"]["message"] = "Steam profile found"
                else:
                    result["info"]["message"] = "Profile not found"
            except Exception as e:
                result["info"]["error"] = str(e)
        else:
            try:
                url = f"https://steamcommunity.com/id/{clean}/?xml=1"
                resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
                text = await resp.text()
                resp.close()
                if "<steamID>" in text:
                    result["exists"] = True
                    name_match = re.search(r'<steamID><!\[CDATA\[(.*?)\]\]></steamID>', text)
                    if name_match:
                        result["info"]["personaname"] = name_match.group(1)
                    id64_match = re.search(r'<steamID64>(\d+)</steamID64>', text)
                    if id64_match:
                        result["info"]["steamid64"] = id64_match.group(1)
                    result["info"]["message"] = "Steam profile found"
                else:
                    result["info"]["message"] = "Profile not found"
            except Exception as e:
                result["info"]["error"] = str(e)
        return result

    async def _check_epic(self, username, timeout, proxy, session):
        result = self.make_result(input=username, platform="epic", valid=True)
        try:
            url = "https://www.epicgames.com/id/api/redirect?clientId=3446cd72694c4a4485d81b77adbb2141&responseType=code"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            status = resp.status
            resp.close()
            result["info"]["status"] = status
            result["info"]["message"] = "Epic Games endpoint reached"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_rockstar(self, username, timeout, proxy, session):
        result = self.make_result(input=username, platform="rockstar", valid=True)
        try:
            url = f"https://scapi.rockstargames.com/profile/getprofile?nickname={username}&maxFriends=3"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy,
                                    headers={"X-Requested-With": "XMLHttpRequest"})
            status = resp.status
            if status == 200:
                data = await resp.json()
                resp.close()
                accounts = data.get("accounts", [])
                if accounts:
                    result["exists"] = True
                    result["info"]["message"] = "Rockstar profile found"
                    result["info"]["rockstarId"] = accounts[0].get("rockstarId", "")
                else:
                    result["info"]["message"] = "Profile not found"
            else:
                resp.close()
                result["info"]["message"] = f"HTTP {status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_origin(self, username, timeout, proxy, session):
        result = self.make_result(input=username, platform="origin", valid=True)
        try:
            url = f"https://api.mozambiquehe.re/nametouid?player={username}&platform=PC"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            status = resp.status
            if status == 200:
                data = await resp.json()
                resp.close()
                if data.get("result"):
                    result["exists"] = True
                    result["info"]["message"] = "EA/Origin account found"
                    result["info"]["uid"] = data.get("result", {}).get("uid", "")
                else:
                    result["info"]["message"] = "Account not found"
            else:
                resp.close()
                result["info"]["message"] = f"HTTP {status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_ubisoft(self, username, timeout, proxy, session):
        result = self.make_result(input=username, platform="ubisoft", valid=True)
        try:
            url = f"https://public-ubiservices.ubi.com/v3/profiles?namesOnPlatform={username}&platformType=uplay"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy,
                                    headers={
                                        "Ubi-AppId": "39baebad-39e5-4552-8c25-2c9b919064e2",
                                        "Content-Type": "application/json",
                                    })
            status = resp.status
            if status == 200:
                data = await resp.json()
                resp.close()
                profiles = data.get("profiles", [])
                if profiles:
                    result["exists"] = True
                    result["info"]["message"] = "Ubisoft profile found"
                    result["info"]["profileId"] = profiles[0].get("profileId", "")
                else:
                    result["info"]["message"] = "Profile not found"
            else:
                resp.close()
                result["info"]["message"] = f"HTTP {status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_riot(self, username, timeout, proxy, session):
        result = self.make_result(input=username, platform="riot", valid=True)
        parts = username.split("#")
        if len(parts) == 2:
            riot_id, tag = parts[0], parts[1]
            try:
                url = "https://account.riotgames.com/"
                resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
                resp.close()
                result["info"]["riot_id"] = riot_id
                result["info"]["tag"] = tag
                result["info"]["message"] = f"Riot ID format valid: {riot_id}#{tag}"
            except Exception as e:
                result["info"]["error"] = str(e)
        else:
            result["info"]["message"] = "Invalid Riot ID format (expected Name#Tag)"
        return result

    async def _check_blizzard(self, username, timeout, proxy, session):
        result = self.make_result(input=username, platform="blizzard", valid=True)
        parts = username.split("#")
        if len(parts) == 2:
            battletag_name, battletag_num = parts[0], parts[1]
            try:
                url = f"https://overwatch.blizzard.com/en-us/career/{battletag_name}-{battletag_num}/"
                resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
                status = resp.status
                text = await resp.text()
                resp.close()
                if status == 200 and "Profile Not Found" not in text:
                    result["exists"] = True
                    result["info"]["message"] = "Blizzard profile found"
                elif "Profile Not Found" in text:
                    result["info"]["message"] = "Profile not found"
                else:
                    result["info"]["message"] = f"HTTP {status}"
            except Exception as e:
                result["info"]["error"] = str(e)
        else:
            result["info"]["message"] = "Invalid BattleTag format (expected Name#1234)"
        return result

    async def _check_xbox(self, gamertag, timeout, proxy, session):
        result = self.make_result(input=gamertag, platform="xbox", valid=True)
        try:
            url = f"https://www.xbox.com/en-US/play/user/{gamertag}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            status = resp.status
            resp.close()
            if status == 200:
                result["exists"] = True
                result["info"]["message"] = "Xbox profile page loaded"
            elif status == 404:
                result["info"]["message"] = "Gamertag not found"
            else:
                result["info"]["message"] = f"HTTP {status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_playstation(self, username, timeout, proxy, session):
        result = self.make_result(input=username, platform="playstation", valid=True)
        try:
            url = f"https://psnprofiles.com/{username}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            status = resp.status
            text = await resp.text()
            resp.close()
            if status == 200:
                if "not-found" in text.lower() or "404" in text:
                    result["info"]["message"] = "PSN profile not found"
                else:
                    result["exists"] = True
                    result["info"]["message"] = "PSN profile found"
            elif status == 404:
                result["info"]["message"] = "PSN profile not found"
            else:
                result["info"]["message"] = f"HTTP {status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result
