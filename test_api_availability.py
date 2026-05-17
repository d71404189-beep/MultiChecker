# -*- coding: utf-8 -*-
"""
Тест доступности API для проверки балансов
"""

import asyncio
import aiohttp
import time


async def test_bitcoin_apis():
    """Тест доступности Bitcoin API"""
    
    print("="*70)
    print("🧪 ТЕСТ ДОСТУПНОСТИ BITCOIN API")
    print("="*70)
    
    # Тестовый адрес с балансом
    test_address = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
    
    apis = [
        ("mempool.space", f"https://mempool.space/api/address/{test_address}"),
        ("blockchain.info", f"https://blockchain.info/q/addressbalance/{test_address}"),
        ("blockchair.com", f"https://api.blockchair.com/bitcoin/dashboards/address/{test_address}"),
    ]
    
    print(f"\n📝 Тестируем API для адреса: {test_address}")
    print("-" * 70)
    
    async with aiohttp.ClientSession() as session:
        for api_name, url in apis:
            print(f"\n🔍 Тест: {api_name}")
            print(f"   URL: {url}")
            
            start_time = time.time()
            
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    elapsed = time.time() - start_time
                    
                    print(f"   Status: {resp.status}")
                    print(f"   Time: {elapsed:.2f}s")
                    
                    if resp.status == 200:
                        content_type = resp.headers.get('Content-Type', '')
                        
                        if 'json' in content_type:
                            data = await resp.json()
                            print(f"   ✅ JSON response received")
                            print(f"   Data keys: {list(data.keys())[:5]}")
                        else:
                            text = await resp.text()
                            print(f"   ✅ Text response: {text[:100]}")
                    elif resp.status == 429:
                        print(f"   ⚠️ Rate limit exceeded")
                    elif resp.status == 403:
                        print(f"   ⚠️ Access forbidden (нужен прокси)")
                    else:
                        print(f"   ❌ Error status")
                        
            except asyncio.TimeoutError:
                elapsed = time.time() - start_time
                print(f"   ❌ Timeout after {elapsed:.2f}s")
            except aiohttp.ClientError as e:
                print(f"   ❌ Connection error: {type(e).__name__}")
            except Exception as e:
                print(f"   ❌ Error: {e}")


async def test_ethereum_apis():
    """Тест доступности Ethereum API"""
    
    print("\n" + "="*70)
    print("🧪 ТЕСТ ДОСТУПНОСТИ ETHEREUM API")
    print("="*70)
    
    # Тестовый адрес
    test_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
    
    apis = [
        ("etherscan.io", f"https://api.etherscan.io/api?module=account&action=balance&address={test_address}&tag=latest"),
        ("cloudflare-eth", "https://cloudflare-eth.com"),
        ("blockchair.com", f"https://api.blockchair.com/ethereum/dashboards/address/{test_address}"),
    ]
    
    print(f"\n📝 Тестируем API для адреса: {test_address}")
    print("-" * 70)
    
    async with aiohttp.ClientSession() as session:
        for api_name, url in apis:
            print(f"\n🔍 Тест: {api_name}")
            print(f"   URL: {url[:80]}...")
            
            start_time = time.time()
            
            try:
                if api_name == "cloudflare-eth":
                    # RPC запрос
                    payload = {
                        "jsonrpc": "2.0",
                        "method": "eth_getBalance",
                        "params": [test_address, "latest"],
                        "id": 1
                    }
                    async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        elapsed = time.time() - start_time
                        print(f"   Status: {resp.status}")
                        print(f"   Time: {elapsed:.2f}s")
                        
                        if resp.status == 200:
                            data = await resp.json()
                            print(f"   ✅ RPC response received")
                            if "result" in data:
                                print(f"   Balance (hex): {data['result'][:20]}...")
                        else:
                            print(f"   ❌ Error status")
                else:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        elapsed = time.time() - start_time
                        print(f"   Status: {resp.status}")
                        print(f"   Time: {elapsed:.2f}s")
                        
                        if resp.status == 200:
                            data = await resp.json()
                            print(f"   ✅ Response received")
                            print(f"   Data keys: {list(data.keys())[:5]}")
                        elif resp.status == 429:
                            print(f"   ⚠️ Rate limit exceeded")
                        elif resp.status == 403:
                            print(f"   ⚠️ Access forbidden (нужен прокси)")
                        else:
                            print(f"   ❌ Error status")
                        
            except asyncio.TimeoutError:
                elapsed = time.time() - start_time
                print(f"   ❌ Timeout after {elapsed:.2f}s")
            except aiohttp.ClientError as e:
                print(f"   ❌ Connection error: {type(e).__name__}")
            except Exception as e:
                print(f"   ❌ Error: {e}")


async def test_solana_apis():
    """Тест доступности Solana API"""
    
    print("\n" + "="*70)
    print("🧪 ТЕСТ ДОСТУПНОСТИ SOLANA API")
    print("="*70)
    
    # Тестовый адрес
    test_address = "7EqQdEULxWcraVx3mXKFjc84LhCkMGZCkRuDpvcMwJeK"
    
    apis = [
        ("solana mainnet", "https://api.mainnet-beta.solana.com"),
        ("solscan.io", f"https://api.solscan.io/account?address={test_address}"),
    ]
    
    print(f"\n📝 Тестируем API для адреса: {test_address}")
    print("-" * 70)
    
    async with aiohttp.ClientSession() as session:
        for api_name, url in apis:
            print(f"\n🔍 Тест: {api_name}")
            print(f"   URL: {url[:80]}...")
            
            start_time = time.time()
            
            try:
                if api_name == "solana mainnet":
                    # RPC запрос
                    payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "getBalance",
                        "params": [test_address]
                    }
                    async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        elapsed = time.time() - start_time
                        print(f"   Status: {resp.status}")
                        print(f"   Time: {elapsed:.2f}s")
                        
                        if resp.status == 200:
                            data = await resp.json()
                            print(f"   ✅ RPC response received")
                            if "result" in data:
                                print(f"   Balance: {data['result']}")
                        else:
                            print(f"   ❌ Error status")
                else:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        elapsed = time.time() - start_time
                        print(f"   Status: {resp.status}")
                        print(f"   Time: {elapsed:.2f}s")
                        
                        if resp.status == 200:
                            data = await resp.json()
                            print(f"   ✅ Response received")
                        elif resp.status == 429:
                            print(f"   ⚠️ Rate limit exceeded")
                        elif resp.status == 403:
                            print(f"   ⚠️ Access forbidden (нужен прокси)")
                        else:
                            print(f"   ❌ Error status")
                        
            except asyncio.TimeoutError:
                elapsed = time.time() - start_time
                print(f"   ❌ Timeout after {elapsed:.2f}s")
            except aiohttp.ClientError as e:
                print(f"   ❌ Connection error: {type(e).__name__}")
            except Exception as e:
                print(f"   ❌ Error: {e}")


async def main():
    """Запуск всех тестов"""
    
    print("\n" + "="*70)
    print("🚀 ДИАГНОСТИКА ДОСТУПНОСТИ API")
    print("="*70)
    print("\nЭтот тест проверит доступность API сервисов для проверки балансов")
    print("Если API недоступны - нужно использовать прокси или API ключи")
    print("="*70)
    
    await test_bitcoin_apis()
    await test_ethereum_apis()
    await test_solana_apis()
    
    print("\n" + "="*70)
    print("📊 РЕКОМЕНДАЦИИ")
    print("="*70)
    print("\n1. Если все API показывают timeout/403:")
    print("   → Используйте прокси (настройте в поле 'Прокси')")
    print("\n2. Если API показывают 429 (rate limit):")
    print("   → Получите API ключи (Etherscan, Blockchair)")
    print("   → Используйте прокси для ротации IP")
    print("\n3. Если некоторые API работают:")
    print("   → Crypto Checker автоматически переключится на рабочие")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
