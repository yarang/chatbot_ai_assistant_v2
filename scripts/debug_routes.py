#!/usr/bin/env python3
"""
Route Debugging Script

현재 애플리케이션에 등록된 모든 경로를 확인합니다.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# Import without triggering full app initialization
# Just check if telegram_router can be imported
try:
    print("telegram_router import 시도...")
    from api.telegram_router import router as telegram_router

    print("✅ telegram_router import 성공!")
    print(f"   Router type: {type(telegram_router)}")
    print(f"   Routes in router: {len(telegram_router.routes)}")

    print("\ntelegram_router의 경로 목록:")
    for route in telegram_router.routes:
        print(f"  - {route.path} ({getattr(route, 'methods', [])})")

except Exception as e:
    print(f"❌ telegram_router import 실패: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)


def check_main_import():
    """Print all registered routes."""
    from main import app

    print("=" * 80)
    print("현재 등록된 모든 경로 (Routes)")
    print("=" * 80)

    routes = []

    for route in app.routes:
        route_info = {
            "path": route.path,
            "methods": getattr(route, "methods", None),
            "name": route.name,
        }

        # Check if route is in API docs
        if hasattr(route, "include_in_schema"):
            route_info["in_schema"] = route.include_in_schema
        else:
            route_info["in_schema"] = "N/A"

        routes.append(route_info)

    # Sort by path
    routes.sort(key=lambda x: x["path"])

    # Print routes
    print(f"\n총 {len(routes)}개의 경로가 등록되어 있습니다.\n")

    for route in routes:
        methods = route["methods"]
        if methods:
            methods_str = ", ".join(sorted(methods))
        else:
            methods_str = "N/A"

        print(f"경로: {route['path']}")
        print(f"  Methods: {methods_str}")
        print(f"  Name: {route['name']}")
        print(f"  In Schema: {route['in_schema']}")

        # 특정 경로 하이라이트
        if "webhook" in route["path"].lower():
            print("  >>>> WEBHOOK 경로 발견! <<<<")
        if "telegram" in route["path"].lower():
            print("  >>>> TELEGRAM 경로 발견! <<<<")

        print()

    # Check specifically for webhook
    print("=" * 80)
    print("Webhook 경로 확인")
    print("=" * 80)

    webhook_routes = [r for r in routes if "webhook" in r["path"].lower()]

    if webhook_routes:
        print(f"\n✅ {len(webhook_routes)}개의 webhook 경로를 찾았습니다:")
        for route in webhook_routes:
            print(f"  - {route['path']} ({route['methods']})")
    else:
        print("\n❌ Webhook 경로를 찾을 수 없습니다!")

    # Check for telegram routes
    print("\n" + "=" * 80)
    print("Telegram 경로 확인")
    print("=" * 80)

    telegram_routes = [r for r in routes if "telegram" in r["path"].lower()]

    if telegram_routes:
        print(f"\n✅ {len(telegram_routes)}개의 telegram 경로를 찾았습니다:")
        for route in telegram_routes:
            print(f"  - {route['path']} ({route['methods']})")
    else:
        print("\n❌ Telegram 경로를 찾을 수 없습니다!")

    # Check OpenAPI schema
    print("\n" + "=" * 80)
    print("OpenAPI Schema 확인")
    print("=" * 80)

    try:
        openapi_schema = app.openapi()
        paths = openapi_schema.get("paths", {})

        print(f"\nOpenAPI Schema에 {len(paths)}개의 경로가 있습니다:\n")

        for path in sorted(paths.keys()):
            print(f"  - {path}")

        if "/webhook" in paths:
            print("\n✅ /webhook이 OpenAPI Schema에 있습니다!")
        else:
            print("\n❌ /webhook이 OpenAPI Schema에 없습니다!")

    except Exception as e:
        print(f"\n❌ OpenAPI Schema 생성 실패: {e}")

    return webhook_routes


if __name__ == "__main__":
    webhook_found = check_main_import()

    if webhook_found:
        print("\n✅ Webhook 경로가 등록되어 있습니다.")
        print("   문제는 다른 곳에 있을 수 있습니다.")
        sys.exit(0)
    else:
        print("\n❌ Webhook 경로가 등록되어 있지 않습니다!")
        print("   telegram_router가 제대로 import되지 않았을 수 있습니다.")
        sys.exit(1)
