import asyncio
import aiohttp
import re
import dns.resolver

from checkers.base_checker import BaseChecker


class EmailChecker(BaseChecker):
    DOMAINS = {
        "gmail.com": "gmail",
        "googlemail.com": "gmail",
        "yahoo.com": "yahoo",
        "yahoo.co.uk": "yahoo",
        "outlook.com": "outlook",
        "hotmail.com": "outlook",
        "live.com": "outlook",
        "protonmail.com": "proton",
        "proton.me": "proton",
        "icloud.com": "icloud",
        "me.com": "icloud",
        "mail.ru": "mailru",
        "inbox.ru": "mailru",
        "list.ru": "mailru",
        "bk.ru": "mailru",
        "yandex.ru": "yandex",
        "yandex.com": "yandex",
        "ya.ru": "yandex",
        "rambler.ru": "rambler",
        "tutanota.com": "tutanota",
        "tuta.io": "tutanota",
    }

    EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

    async def check(self, email: str, timeout: int = 10, proxy: str = None, session: aiohttp.ClientSession = None) -> dict:
        result = self.make_result(input=email, email=email, domain="", service="email")

        if not self.EMAIL_RE.match(email):
            result["info"]["error"] = "Invalid email format"
            return result

        domain = email.split("@")[1].lower()
        result["domain"] = domain
        result["valid"] = True

        checker_name = self.DOMAINS.get(domain)

        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession()

        try:
            if checker_name == "gmail":
                result = await self._check_gmail(email, timeout, proxy, session)
            elif checker_name == "yahoo":
                result = await self._check_yahoo(email, timeout, proxy, session)
            elif checker_name == "outlook":
                result = await self._check_outlook(email, timeout, proxy, session)
            elif checker_name == "proton":
                result = await self._check_protonmail(email, timeout, proxy, session)
            elif checker_name == "icloud":
                result = await self._check_icloud(email, timeout, proxy, session)
            elif checker_name == "mailru":
                result = await self._check_mailru(email, timeout, proxy, session)
            elif checker_name == "yandex":
                result = await self._check_yandex(email, timeout, proxy, session)
            elif checker_name == "rambler":
                result = await self._check_rambler(email, timeout, proxy, session)
            elif checker_name == "tutanota":
                result = await self._check_tutanota(email, timeout, proxy, session)
            else:
                result = await self._check_mx(email, domain, timeout, proxy, session)
        finally:
            if own_session:
                await session.close()

        return result

    async def _check_mx(self, email, domain, timeout, proxy, session):
        result = self.make_result(input=email, email=email, domain=domain, valid=True, service="email")
        try:
            loop = asyncio.get_event_loop()
            answers = await loop.run_in_executor(None, lambda: dns.resolver.resolve(domain, 'MX'))
            mx_records = [str(r.exchange).rstrip('.') for r in answers]
            result["info"]["mx_records"] = mx_records
            if mx_records:
                result["exists"] = True
                result["info"]["message"] = f"Domain has {len(mx_records)} MX record(s)"
            else:
                result["info"]["message"] = "No MX records found"
        except dns.resolver.NXDOMAIN:
            result["info"]["message"] = "Domain does not exist"
        except dns.resolver.NoAnswer:
            result["info"]["message"] = "No MX records"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_gmail(self, email, timeout, proxy, session):
        result = self.make_result(input=email, email=email, domain="gmail.com", valid=True, service="email")
        try:
            url = "https://accounts.google.com/AccountChooser"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy,
                                    params={"Email": email, "flowName": "GlifWebSignIn"})
            text = await resp.text()
            resp.close()
            if "couldn't find your google account" in text.lower():
                result["info"]["message"] = "Account not found"
            else:
                result["exists"] = True
                result["info"]["message"] = "Google account likely exists"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_yahoo(self, email, timeout, proxy, session):
        result = self.make_result(input=email, email=email, domain="yahoo.com", valid=True, service="email")
        try:
            url = "https://login.yahoo.com/"
            resp = await self.fetch(session, "POST", url, timeout=timeout, proxy=proxy,
                                    data={"username": email},
                                    headers={"Content-Type": "application/x-www-form-urlencoded"})
            text = await resp.text()
            resp.close()
            if "Sorry, we don" in text or "doesn't exist" in text.lower():
                result["info"]["message"] = "Account not found"
            else:
                result["exists"] = True
                result["info"]["message"] = "Yahoo account likely exists"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_outlook(self, email, timeout, proxy, session):
        result = self.make_result(input=email, email=email, domain="outlook.com", valid=True, service="email")
        try:
            url = "https://login.microsoftonline.com/common/GetCredentialType"
            payload = {"username": email, "isOtherIdpSupported": True, "checkPhones": False}
            resp = await self.fetch(session, "POST", url, timeout=timeout, proxy=proxy,
                                    json=payload,
                                    headers={"Content-Type": "application/json"})
            data = await resp.json()
            resp.close()
            if_exists = data.get("IfExistsResult", 1)
            if if_exists == 0:
                result["exists"] = True
                result["info"]["message"] = "Microsoft account exists"
            elif if_exists == 1:
                result["info"]["message"] = "Account not found"
            else:
                result["info"]["message"] = f"IfExistsResult={if_exists}"
            result["info"]["throttle"] = data.get("ThrottleStatus", 0)
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_protonmail(self, email, timeout, proxy, session):
        result = self.make_result(input=email, email=email, domain="protonmail.com", valid=True, service="email")
        try:
            username = email.split("@")[0]
            url = f"https://mail.proton.me/api/users/available?Name={username}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            status = resp.status
            resp.close()
            if status == 409:
                result["exists"] = True
                result["info"]["message"] = "Proton account exists (username taken)"
            elif status == 200:
                result["info"]["message"] = "Username available (account may not exist)"
            else:
                result["info"]["message"] = f"HTTP {status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_icloud(self, email, timeout, proxy, session):
        result = self.make_result(input=email, email=email, domain="icloud.com", valid=True, service="email")
        try:
            url = "https://iforgot.apple.com/password/verify/appleid"
            resp = await self.fetch(session, "POST", url, timeout=timeout, proxy=proxy,
                                    json={"id": email},
                                    headers={"Content-Type": "application/json",
                                             "Accept": "application/json"})
            status = resp.status
            text = await resp.text()
            resp.close()
            if status == 200 or "found" in text.lower():
                result["exists"] = True
                result["info"]["message"] = "Apple ID likely exists"
            elif status == 404 or "not found" in text.lower():
                result["info"]["message"] = "Apple ID not found"
            else:
                result["info"]["message"] = f"HTTP {status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_mailru(self, email, timeout, proxy, session):
        result = self.make_result(input=email, email=email, domain="mail.ru", valid=True, service="email")
        try:
            url = "https://account.mail.ru/api/v1/user/exists"
            resp = await self.fetch(session, "POST", url, timeout=timeout, proxy=proxy,
                                    data={"email": email},
                                    headers={"Content-Type": "application/x-www-form-urlencoded"})
            data = await resp.json()
            resp.close()
            if data.get("body", {}).get("exists"):
                result["exists"] = True
                result["info"]["message"] = "Mail.ru account exists"
            else:
                result["info"]["message"] = "Account not found"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_yandex(self, email, timeout, proxy, session):
        result = self.make_result(input=email, email=email, domain="yandex.ru", valid=True, service="email")
        try:
            login = email.split("@")[0]
            url = "https://passport.yandex.ru/registration-validations/checkLogin"
            resp = await self.fetch(session, "POST", url, timeout=timeout, proxy=proxy,
                                    data={"login": login, "track_id": ""},
                                    headers={"Content-Type": "application/x-www-form-urlencoded"})
            data = await resp.json()
            resp.close()
            status_val = data.get("status")
            if status_val == "ok":
                result["info"]["message"] = "Login available (account may not exist)"
            else:
                result["exists"] = True
                result["info"]["message"] = "Yandex account likely exists"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_rambler(self, email, timeout, proxy, session):
        result = self.make_result(input=email, email=email, domain="rambler.ru", valid=True, service="email")
        try:
            url = "https://id.rambler.ru/api/v3/legacy/check-login"
            resp = await self.fetch(session, "POST", url, timeout=timeout, proxy=proxy,
                                    json={"login": email},
                                    headers={"Content-Type": "application/json"})
            data = await resp.json()
            resp.close()
            if data.get("status") == "exists" or data.get("result") == "exists":
                result["exists"] = True
                result["info"]["message"] = "Rambler account exists"
            elif data.get("error"):
                result["exists"] = True
                result["info"]["message"] = "Rambler account likely exists"
            else:
                result["info"]["message"] = "Account not found or login available"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_tutanota(self, email, timeout, proxy, session):
        result = self.make_result(input=email, email=email, domain="tutanota.com", valid=True, service="email")
        try:
            loop = asyncio.get_event_loop()
            answers = await loop.run_in_executor(
                None, lambda: dns.resolver.resolve("tutanota.com", 'MX'))
            mx_records = [str(r.exchange).rstrip('.') for r in answers]
            result["info"]["mx_records"] = mx_records
            if mx_records:
                result["exists"] = True
                result["info"]["message"] = "Tutanota domain verified, email likely valid"
            else:
                result["info"]["message"] = "Could not verify domain"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result
