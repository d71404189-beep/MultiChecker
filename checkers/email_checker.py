import asyncio
import aiohttp
import re

class EmailChecker:
    DOMAINS = {
        "gmail.com": {"check": "gmail", "recovery": True},
        "yahoo.com": {"check": "yahoo", "recovery": True},
        "outlook.com": {"check": "outlook", "recovery": True},
        "hotmail.com": {"check": "hotmail", "recovery": True},
        "protonmail.com": {"check": "proton", "recovery": True},
        "icloud.com": {"check": "icloud", "recovery": True},
        "mail.ru": {"check": "mailru", "recovery": True},
        "yandex.ru": {"check": "yandex", "recovery": True},
        "rambler.ru": {"check": "rambler", "recovery": True},
        "tutanota.com": {"check": "tutanota", "recovery": True},
    }
    
    def __init__(self):
        self.session = None
    
    async def check(self, email: str, timeout: int = 10) -> dict:
        result = {
            "email": email,
            "valid": False,
            "exists": False,
            "domain": "",
            "info": {}
        }
        
        if not self._validate_email(email):
            result["info"]["error"] = "Invalid email format"
            return result
        
        domain = email.split("@")[1].lower()
        result["domain"] = domain
        
        if domain in self.DOMAINS:
            checker = self.DOMAINS[domain]
            if checker["check"] == "gmail":
                result = await self._check_gmail(email, timeout)
            elif checker["check"] == "yahoo":
                result = await self._check_yahoo(email, timeout)
            elif checker["check"] == "outlook":
                result = await self._check_outlook(email, timeout)
            elif checker["check"] == "hotmail":
                result = await self._check_hotmail(email, timeout)
            elif checker["check"] == "proton":
                result = await self._check_protonmail(email, timeout)
            elif checker["check"] == "icloud":
                result = await self._check_icloud(email, timeout)
            elif checker["check"] == "mailru":
                result = await self._check_mailru(email, timeout)
            elif checker["check"] == "yandex":
                result = await self._check_yandex(email, timeout)
            elif checker["check"] == "rambler":
                result = await self._check_rambler(email, timeout)
            elif checker["check"] == "tutanota":
                result = await self._check_tutanota(email, timeout)
        else:
            result["info"]["error"] = f"Domain {domain} not supported"
        
        return result
    
    def _validate_email(self, email: str) -> bool:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    async def _check_gmail(self, email: str, timeout: int) -> dict:
        result = {"email": email, "valid": True, "exists": False, "domain": "gmail.com", "info": {}}
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://mail.google.com/mx/relay?email={email}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    result["info"]["mx_check"] = resp.status
        except Exception as e:
            result["info"]["error"] = str(e)
        
        return result
    
    async def _check_yahoo(self, email: str, timeout: int) -> dict:
        result = {"email": email, "valid": True, "exists": False, "domain": "yahoo.com", "info": {}}
        return result
    
    async def _check_outlook(self, email: str, timeout: int) -> dict:
        result = {"email": email, "valid": True, "exists": False, "domain": "outlook.com", "info": {}}
        return result
    
    async def _check_hotmail(self, email: str, timeout: int) -> dict:
        result = {"email": email, "valid": True, "exists": False, "domain": "hotmail.com", "info": {}}
        return result
    
    async def _check_protonmail(self, email: str, timeout: int) -> dict:
        result = {"email": email, "valid": True, "exists": False, "domain": "protonmail.com", "info": {}}
        return result
    
    async def _check_icloud(self, email: str, timeout: int) -> dict:
        result = {"email": email, "valid": True, "exists": False, "domain": "icloud.com", "info": {}}
        return result
    
    async def _check_mailru(self, email: str, timeout: int) -> dict:
        result = {"email": email, "valid": True, "exists": False, "domain": "mail.ru", "info": {}}
        return result
    
    async def _check_yandex(self, email: str, timeout: int) -> dict:
        result = {"email": email, "valid": True, "exists": False, "domain": "yandex.ru", "info": {}}
        return result
    
    async def _check_rambler(self, email: str, timeout: int) -> dict:
        result = {"email": email, "valid": True, "exists": False, "domain": "rambler.ru", "info": {}}
        return result
    
    async def _check_tutanota(self, email: str, timeout: int) -> dict:
        result = {"email": email, "valid": True, "exists": False, "domain": "tutanota.com", "info": {}}
        return result
