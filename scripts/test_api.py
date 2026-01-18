#!/usr/bin/env python3
"""API 엔드포인트 테스트 스크립트"""
import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8888"

def test_endpoint(path):
    """엔드포인트 테스트"""
    url = f"{BASE_URL}{path}"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            response.read().decode('utf-8')
            print(f"✅ {path}")
            return True
    except urllib.error.HTTPError as e:
        print(f"⚠️  {path} - HTTP {e.code}: {e.reason}")
        return e.code != 404
    except urllib.error.URLError as e:
        print(f"❌ {path} - Connection error: {e.reason}")
        return False
    except Exception as e:
        print(f"❌ {path} - Error: {e}")
        return False

def main():
    print("="*60)
    print("API 엔드포인트 테스트")
    print("="*60)
    print(f"서버: {BASE_URL}")
    print()

    # OpenAPI Schema 확인
    print("1. OpenAPI Schema 확인...")
    try:
        with urllib.request.urlopen(f"{BASE_URL}/openapi.json", timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            paths = list(data.get('paths', {}).keys())
            print(f"✅ OpenAPI Schema 로드됨 (총 {len(paths)}개 경로)")

            # Webhook 확인
            webhook_paths = [p for p in paths if 'webhook' in p.lower()]
            telegram_paths = [p for p in paths if 'telegram' in p.lower()]

            print(f"\n📱 Webhook 경로: {len(webhook_paths)}개")
            for p in webhook_paths:
                print(f"   {p}")

            print(f"\n📱 Telegram 경로: {len(telegram_paths)}개")
            for p in telegram_paths:
                print(f"   {p}")

    except Exception as e:
        print(f"❌ OpenAPI Schema 로드 실패: {e}")

    print("\n2. 주요 엔드포인트 테스트...")
    test_paths = [
        "/telegram/test",
        "/webhook",
        "/api/persona/user/me",
        "/docs",
        "/",
    ]

    results = []
    for path in test_paths:
        results.append(test_endpoint(path))

    print("\n" + "="*60)
    success = sum(1 for r in results if r)
    print(f"테스트 완료: {success}/{len(results)} 성공")
    print("="*60)

if __name__ == "__main__":
    main()
