"""Automated integration test for agents-browser high-level tools."""

import asyncio
from agents_browser.cdp import CDPClient


async def run_test():
    print("Testing CDPClient in headless mode...")
    client = CDPClient(headless=True)
    try:
        await client.connect()
        print("Connected!")

        # 1. Test Web Search
        print("\n1. Testing High-Level Search ('python fastmcp')...")
        search_res = await client.search("python fastmcp")
        print("Search Results snippet:\n", search_res[:350])
        assert "Search Results" in search_res or "fastmcp" in search_res.lower()

        # 2. Test Direct Article Reading (Wikipedia)
        print("\n2. Testing High-Level Article Reader (Wikipedia Python)...")
        await client.open("https://en.wikipedia.org/wiki/Python_(programming_language)")
        await asyncio.sleep(1.0)
        article_md = await client.read_article()
        print("Reader-Mode snippet:\n", article_md[:350])
        assert "Python" in article_md

        # 3. Test Structured Scrape
        print("\n3. Testing Structured Scraper (links mode)...")
        links_md = await client.scrape(selector=".infobox", mode="links")
        print("Scraped Links snippet:\n", links_md[:200])

        print("\n4. Testing Full-page Screenshot...")
        b64 = await client.screenshot(full_page=False)
        assert len(b64) > 1000

        print("\nAll High-Level Built-in Tools PASSED!")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(run_test())
