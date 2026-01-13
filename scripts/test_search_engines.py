#!/usr/bin/env python3
"""
Web Search Engine Test Script

Tests all supported search engines:
- DuckDuckGo (default, free)
- Tavily (requires API key)
- Google Custom Search (requires API key + CSE ID)
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import get_settings
from tools.search_tool import (
    get_search_tool,
    get_ddg_search_tool,
    get_tavily_search_tool,
    get_google_search_tool,
)


async def test_search_engine(engine_name: str, search_tool):
    """Test a search engine with a sample query."""
    print(f"\n{'='*60}")
    print(f"Testing {engine_name}")
    print(f"{'='*60}")

    try:
        # Test query
        query = "Python LangGraph tutorial"
        print(f"Query: {query}")
        print(f"Tool: {search_tool.name}")
        print(f"Description: {search_tool.description[:100]}...")

        # Execute search
        print("\nExecuting search...")
        result = await search_tool.ainvoke(query)

        print(f"\n✅ Search successful!")
        print(f"\nResult preview:")
        print("-" * 60)
        if isinstance(result, list):
            for i, item in enumerate(result[:2], 1):  # Show first 2 results
                print(f"\n[{i}] {str(item)[:200]}...")
        else:
            print(f"{str(result)[:500]}...")

        print(f"\n✅ {engine_name} is working correctly!")
        return True

    except Exception as e:
        print(f"\n❌ {engine_name} test failed!")
        print(f"Error: {type(e).__name__}: {e}")
        return False


async def main():
    """Run all search engine tests."""
    settings = get_settings()

    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "Web Search Engine Test" + " "*21 + "║")
    print("╚" + "="*58 + "╝")

    results = {}

    # Test 1: DuckDuckGo (default, should always work)
    print("\n🦆 DuckDuckGo Search (Default, Free)")
    try:
        ddg_tool = get_ddg_search_tool(max_results=2)
        results["DuckDuckGo"] = await test_search_engine("DuckDuckGo", ddg_tool)
    except Exception as e:
        print(f"❌ Failed to initialize DuckDuckGo: {e}")
        results["DuckDuckGo"] = False

    # Test 2: Tavily (if API key available)
    tavily_key = settings.search.tavily_api_key or settings.tavily_api_key
    if tavily_key:
        print("\n🔍 Tavily Search (Premium)")
        try:
            tavily_tool = get_tavily_search_tool(api_key=tavily_key, max_results=2)
            results["Tavily"] = await test_search_engine("Tavily", tavily_tool)
        except Exception as e:
            print(f"❌ Failed to initialize Tavily: {e}")
            results["Tavily"] = False
    else:
        print("\n⏭️  Skipping Tavily (no API key configured)")

    # Test 3: Google Custom Search (if API key + CSE ID available)
    google_key = settings.search.google_api_key
    google_cse = settings.search.google_cse_id
    if google_key and google_cse:
        print("\n🌐 Google Custom Search")
        try:
            google_tool = get_google_search_tool(
                api_key=google_key,
                cse_id=google_cse,
                max_results=2,
            )
            results["Google"] = await test_search_engine("Google Custom Search", google_tool)
        except Exception as e:
            print(f"❌ Failed to initialize Google: {e}")
            results["Google"] = False
    else:
        print("\n⏭️  Skipping Google (no API key or CSE ID configured)")

    # Test 4: Current configured engine
    print("\n\n🔧 Testing Configured Search Engine")
    print(f"Current engine: {settings.search.engine}")
    try:
        configured_tool = get_search_tool()
        results["Configured"] = await test_search_engine(
            f"Configured ({settings.search.engine})", configured_tool
        )
    except Exception as e:
        print(f"❌ Failed to initialize configured engine: {e}")
        results["Configured"] = False

    # Summary
    print("\n\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)

    for engine, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{engine:20s} - {status}")

    total = len(results)
    passed = sum(results.values())

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All search engines are working correctly!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check configuration.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
