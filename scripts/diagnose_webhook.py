#!/usr/bin/env python3
"""
Webhook Diagnosis Script

이 스크립트는 webhook 문제를 진단하고 해결 방안을 제시합니다.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import get_settings
import httpx
import subprocess


async def check_server_status(settings):
    """서버 실행 상태 확인"""
    print("\n" + "="*60)
    print("1. 서버 실행 상태 확인")
    print("="*60)

    webhook_url = settings.telegram.webhook_url
    if not webhook_url:
        print("❌ TELEGRAM_WEBHOOK_URL이 설정되지 않았습니다.")
        print("   .env 파일에 TELEGRAM_WEBHOOK_URL=http://localhost:8000/webhook 를 설정하세요.")
        return False

    # URL에서 도메인 추출
    from urllib.parse import urlparse
    parsed = urlparse(webhook_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    print(f"📡 Webhook URL: {webhook_url}")
    print(f"📡 Base URL: {base_url}")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Health check (루트 경로)
            response = await client.get(base_url)
            print(f"✅ 서버가 실행 중입니다 (Status: {response.status_code})")

            # Webhook 엔드포인트 확인 (OPTIONS 요청)
            webhook_response = await client.options(webhook_url)
            print(f"✅ Webhook 엔드포인트 존재 (Status: {webhook_response.status_code})")

            return True

    except httpx.ConnectError:
        print(f"❌ 서버에 연결할 수 없습니다: {base_url}")
        print("   서버가 실행 중인지 확인하세요:")
        print("   uvicorn main:app --reload")
        return False

    except httpx.TimeoutException:
        print(f"❌ 서버 응답 시간 초과: {base_url}")
        print("   서버가 느리게 응답하고 있습니다.")
        return False

    except Exception as e:
        print(f"❌ 서버 확인 중 오류 발생: {e}")
        return False


async def check_webhook_info(settings):
    """Telegram Webhook 정보 조회"""
    print("\n" + "="*60)
    print("2. Telegram Webhook 정보 조회")
    print("="*60)

    bot_token = settings.telegram.bot_token
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN이 설정되지 않았습니다.")
        return False

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
            )
            data = response.json()

            if not data.get("ok"):
                print(f"❌ Telegram API 오류: {data.get('description')}")
                return False

            webhook_info = data.get("result", {})
            url = webhook_info.get("url", "")
            has_custom_certificate = webhook_info.get("has_custom_certificate", False)
            pending_update_count = webhook_info.get("pending_update_count", 0)
            last_error_date = webhook_info.get("last_error_date")
            last_error_message = webhook_info.get("last_error_message", "")

            print(f"📡 등록된 Webhook URL: {url if url else '(없음)'}")
            print(f"🔒 인증서 사용: {'예' if has_custom_certificate else '아니오'}")
            print(f"📨 대기 중인 업데이트: {pending_update_count}")

            if last_error_date:
                from datetime import datetime
                error_time = datetime.fromtimestamp(last_error_date)
                print(f"❌ 마지막 오류 ({error_time}):")
                print(f"   {last_error_message}")

            if not url:
                print("\n⚠️  Webhook이 설정되지 않았습니다.")
                return False
            else:
                print("\n✅ Webhook이 설정되어 있습니다.")

                # URL 검증
                expected_url = settings.telegram.webhook_url
                if url != expected_url:
                    print("\n⚠️  Webhook URL이 일치하지 않습니다!")
                    print(f"   예상: {expected_url}")
                    print(f"   실제: {url}")
                    print("\n   Webhook을 재설정해야 합니다.")
                    return False
                else:
                    print("✅ Webhook URL이 정확합니다.")

                return True

    except Exception as e:
        print(f"❌ Telegram API 요청 중 오류: {e}")
        return False


def check_ngrok_settings(settings):
    """ngrok 설정 확인"""
    print("\n" + "="*60)
    print("3. ngrok/도메인 설정 확인")
    print("="*60)

    webhook_url = settings.telegram.webhook_url
    if not webhook_url:
        print("❌ TELEGRAM_WEBHOOK_URL이 설정되지 않았습니다.")
        return False

    if "ngrok" in webhook_url:
        print(f"⚠️  ngrok를 사용 중입니다: {webhook_url}")
        print("\nngrok 사용 시 주의사항:")
        print("1. ngrok가 실행 중이어야 합니다:")
        print("   ngrok http 8000")
        print("\n2. ngrok URL은 매번 변경됩니다.")
        print("   BotFather에서 Webhook URL을 업데이트해야 합니다.")
        print("\n3. 무료 ngrok은 요청 제한이 있습니다.")
        print("   프로덕션에서는 안정적인 도메인을 사용하세요.")

        # ngrok 프로세스 확인
        try:
            result = subprocess.run(["pgrep", "-f", "ngrok"], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ ngrok 프로세스가 실행 중입니다.")
            else:
                print("❌ ngrok가 실행 중이 아닙니다.")
                print("   'ngrok http 8000' 명령어로 시작하세요.")
                return False
        except Exception as e:
            print(f"⚠️  ngrok 프로세스 확인 실패: {e}")

    elif "localhost" in webhook_url or "127.0.0.1" in webhook_url:
        print(f"⚠️  localhost URL은 외부에서 접근할 수 없습니다: {webhook_url}")
        print("   ngrok 또는 공개 도메인을 사용하세요.")

    else:
        print(f"✅ 도메인 URL: {webhook_url}")

    return True


def show_webhook_setup_command(settings):
    """Webhook 설정 명령어 표시"""
    print("\n" + "="*60)
    print("4. Webhook 설정 방법")
    print("="*60)

    bot_token = settings.telegram.bot_token
    webhook_url = settings.telegram.webhook_url
    webhook_secret = settings.telegram.webhook_secret

    if not bot_token or not webhook_url:
        print("❌ 필요한 설정이 누락되었습니다.")
        return

    print("\nWebhook을 설정하려면 다음 명령어를 실행하세요:\n")

    if webhook_secret:
        # 시크릿 토큰 있는 경우
        print("```bash")
        print(f"curl -X POST 'https://api.telegram.org/bot{bot_token}/setWebhook' \\")
        print(f"  -d 'url={webhook_url}' \\")
        print(f"  -d 'secret_token={webhook_secret}'")
        print("```")
    else:
        # 시크릿 토큰 없는 경우
        print("```bash")
        print(f"curl -X POST 'https://api.telegram.org/bot{bot_token}/setWebhook' \\")
        print(f"  -d 'url={webhook_url}'")
        print("```")

    print("\n또는 Python 스크립트로:")
    print("```bash")
    print("python scripts/set_webhook.py")
    print("```\n")

    print("⚠️  주의: 시크릿 토큰을 사용하는 경우 webhook 설정 시 반드시 포함해야 합니다.")


async def main():
    """메인 진단 함수"""
    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "Webhook 진단 도구" + " "*23 + "║")
    print("╚" + "="*58 + "╝")

    settings = get_settings()

    # 1. 서버 상태 확인
    server_ok = await check_server_status(settings)

    # 2. Telegram webhook 정보 확인
    webhook_ok = await check_webhook_info(settings)

    # 3. ngrok/도메인 설정 확인
    ngrok_ok = check_ngrok_settings(settings)

    # 4. Webhook 설정 명령어 표시
    show_webhook_setup_command(settings)

    # 요약
    print("\n" + "="*60)
    print("📊 진단 결과 요약")
    print("="*60)

    results = {
        "서버 실행 상태": server_ok,
        "Telegram Webhook": webhook_ok,
        "ngrok/도메인 설정": ngrok_ok,
    }

    for name, ok in results.items():
        status = "✅ 정상" if ok else "❌ 문제 있음"
        print(f"{name:20s}: {status}")

    all_ok = all(results.values())

    if all_ok:
        print("\n🎉 모든 항목이 정상입니다!")
        print("   Webhook이 제대로 작동해야 합니다.")
        return 0
    else:
        print("\n⚠️  일부 항목에 문제가 있습니다.")
        print("   위의 지시사항을 따라 문제를 해결하세요.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
