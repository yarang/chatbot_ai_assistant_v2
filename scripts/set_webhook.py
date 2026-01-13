#!/usr/bin/env python3
"""
Webhook Setup Script

Telegram Bot Webhook을 설정하는 스크립트입니다.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import get_settings
import httpx


async def set_webhook():
    """Webhook 설정"""
    settings = get_settings()

    bot_token = settings.telegram.bot_token
    webhook_url = settings.telegram.webhook_url
    webhook_secret = settings.telegram.webhook_secret

    print("╔" + "="*58 + "╗")
    print("║" + " "*20 + "Webhook 설정" + " "*27 + "║")
    print("╚" + "="*58 + "╝")

    # 필수 값 확인
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN이 설정되지 않았습니다.")
        print("   .env 파일에 TELEGRAM_BOT_TOKEN을 설정하세요.")
        return 1

    if not webhook_url:
        print("❌ TELEGRAM_WEBHOOK_URL이 설정되지 않았습니다.")
        print("   .env 파일에 TELEGRAM_WEBHOOK_URL을 설정하세요.")
        print("   예: TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook")
        return 1

    print(f"\n📡 Webhook URL: {webhook_url}")
    if webhook_secret:
        print(f"🔒 Secret Token: {'*' * 20} (설정됨)")
    else:
        print("⚠️  Secret Token: 미설정 (보안 권장)")

    # Webhook 설정 요청
    print("\nWebhook을 설정하는 중...")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            params = {"url": webhook_url}
            if webhook_secret:
                params["secret_token"] = webhook_secret

            response = await client.post(
                f"https://api.telegram.org/bot{bot_token}/setWebhook",
                params=params
            )

            data = response.json()

            if data.get("ok"):
                print("✅ Webhook이 성공적으로 설정되었습니다!")
                print("\n설정 정보:")
                result = data.get("result", {})
                print(f"  - URL: {result.get('url', 'N/A')}")
                print(f"  - 인증서: {'사용' if result.get('has_custom_certificate') else '미사용'}")
                print(f"  - 최대 연결: {result.get('max_connections', 'N/A')}")
                print(f"  - 허용된 업데이트: {result.get('allowed_updates', 'all')}")

                # Webhook 정보 조회
                print("\n현재 Webhook 정보를 확인합니다...")
                info_response = await client.get(
                    f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
                )
                info_data = info_response.json()

                if info_data.get("ok"):
                    webhook_info = info_data.get("result", {})
                    pending = webhook_info.get("pending_update_count", 0)
                    if pending > 0:
                        print(f"\n⚠️  대기 중인 업데이트: {pending}")
                        print("   Webhook이 정상 작동하지 않을 수 있습니다.")

                return 0
            else:
                print(f"❌ Webhook 설정 실패!")
                print(f"   오류: {data.get('description', 'Unknown error')}")
                return 1

    except httpx.ConnectError:
        print("❌ Telegram API에 연결할 수 없습니다.")
        print("   인터넷 연결을 확인하세요.")
        return 1

    except httpx.TimeoutException:
        print("❌ 요청 시간 초과")
        return 1

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return 1


async def delete_webhook():
    """Webhook 삭제"""
    settings = get_settings()

    bot_token = settings.telegram.bot_token

    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN이 설정되지 않았습니다.")
        return 1

    print("\nWebhook을 삭제하는 중...")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{bot_token}/deleteWebhook"
            )

            data = response.json()

            if data.get("ok"):
                print("✅ Webhook이 성공적으로 삭제되었습니다!")
                print("   이제 봇은 Webhook이 아닌 Polling 모드로 작동합니다.")
                return 0
            else:
                print(f"❌ Webhook 삭제 실패!")
                print(f"   오류: {data.get('description', 'Unknown error')}")
                return 1

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return 1


async def main():
    """메인 함수"""
    if len(sys.argv) > 1 and sys.argv[1] == "--delete":
        await delete_webhook()
    else:
        await set_webhook()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
