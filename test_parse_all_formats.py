# -*- coding: utf-8 -*-
"""
Тест парсинга всех форматов credentials со скриншота пользователя
"""
import sys
sys.path.insert(0, ".")
from checkers.crypto_checker import CryptoChecker

checker = CryptoChecker()

# Все реальные форматы со скриншота
test_cases = [
    # (входная строка, ожидаемый_login, ожидаемый_pass)
    ("kucoin.com:151951:Gregre20",                                                          "151951",                   "Gregre20"),
    ("accounts.binance.com/pt/login:9314177:laranjeirA228230",                             "9314177",                  "laranjeirA228230"),
    ("okx.com/join/26369401:password:@realwawonee89",                                      "password",                 "@realwawonee89"),
    ("accounts.binance.com/en/login:0348578l840:Naeem.123:Channel",                        "0348578l840",              "Naeem.123:Channel"),
    ("com.binance.dev:/mobyevansjones@gmail.com:@",                                        "mobyevansjones@gmail.com", "@"),
    ("futures.kucoin.com:gececi164@gmail.com:21532456s",                                   "gececi164@gmail.com",      "21532456s"),
    ("accounts.kucoin.com/es-la/register:jorekina@gmail.com:jorekina@92",                  "jorekina@gmail.com",       "jorekina@92"),
    ("accounts.binance.com/es-AR/register:clearwaterservicios@gmail.com:%6E[p",            "clearwaterservicios@gmail.com", "%6E[p"),
    ("com.binance.com:arsalbaba2003@gmail.com:Ars12m0316",                                 "arsalbaba2003@gmail.com",  "Ars12m0316"),
    ("kucoin.com/ucenter/signin:crysthianmarcos87@gmail.com:23%kucoin%6052",               "crysthianmarcos87@gmail.com", "23%kucoin%6052"),
    ("accounts.binance.com:zkkaa707@gmail.com:Sk<3As??",                                   "zkkaa707@gmail.com",       "Sk<3As??"),
    ("gate.io:/neko1325:Fuckchina",                                                        "neko1325",                 "Fuckchina"),
    ("bybit.com/en-us/register:dillonirussell@gmail.com:cerat1423",                        "dillonirussell@gmail.com", "cerat1423"),
    ("gate.io:skuba21@gmail.com:@lencia2020",                                              "skuba21@gmail.com",        "@lencia2020"),
    ("binance.com:fahidxx999@gmail.com:Adgjmp1998@",                                       "fahidxx999@gmail.com",     "Adgjmp1998@"),
    ("kucoin.com/:AMIIIR.02@gmail.com:10am12i168ir",                                       "AMIIIR.02@gmail.com",      "10am12i168ir"),
    ("bitget.com:zeeabbas744@gmail.com:zee3213210",                                        "zeeabbas744@gmail.com",    "zee3213210"),
    ("accounts.binance.com/es/login-password:darwinlopez679@gmail.com:1089907396Lopez",    "darwinlopez679@gmail.com", "1089907396Lopez"),
    ("accounts.binance.com:zeoqeli01@gmail.com:Nattawatpeo00",                             "zeoqeli01@gmail.com",      "Nattawatpeo00"),
    # Стандартные форматы
    ("user@binance.com:password123",                                                        "user@binance.com",         "password123"),
    ("https://accounts.binance.com/en/login:user@mail.com:pass123",                        "user@mail.com",            "pass123"),
    ("binance:user@mail.com:pass123",                                                       "user@mail.com",            "pass123"),
]

print("=" * 80)
print("🧪 ТЕСТ ПАРСИНГА ВСЕХ ФОРМАТОВ CREDENTIALS")
print("=" * 80)

passed = 0
failed = 0

for line, exp_login, exp_pass in test_cases:
    login, password = checker._parse_credentials(line)
    ok = (login == exp_login and password == exp_pass)
    status = "✅" if ok else "❌"
    if ok:
        passed += 1
    else:
        failed += 1
        print(f"\n{status} FAIL: {line[:70]}")
        print(f"   Ожидалось: login={exp_login!r}  pass={exp_pass!r}")
        print(f"   Получено:  login={login!r}  pass={password!r}")

print(f"\n{'='*80}")
print(f"📊 ИТОГ: {passed}/{len(test_cases)} прошло  |  {failed} провалено")
print("=" * 80)
