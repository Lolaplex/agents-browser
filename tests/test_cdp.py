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

        # 4. Test Scroll & In-Page Find
        print("\n4. Testing Scroll and In-Page Find...")
        scroll_res = await client.scroll("down", 500)
        assert "Scrolled" in scroll_res
        find_res = await client.find_in_page("Guido")
        assert "Guido" in find_res

        # 5. Test Wait Stable
        print("\n5. Testing Wait Stable...")
        stable_res = await client.wait_stable(timeout_ms=3000, quiet_ms=200)
        assert "stable" in stable_res.lower() or "timeout" in stable_res.lower()

        # 6. Test Screenshot
        print("\n6. Testing Full-page Screenshot...")
        b64 = await client.screenshot(full_page=False)
        assert len(b64) > 1000

        # 7. Test Fast Fetch (non-DOM)
        print("\n7. Testing Fast Non-DOM Fetch...")
        fetch_res = await client.fetch("https://httpbin.org/get")
        assert "HTTP 200 GET" in fetch_res
        assert "application/json" in fetch_res

        # 8. Test Download via Click
        print("\n8. Testing Download via Click...")
        import tempfile
        from pathlib import Path
        td = Path(tempfile.mkdtemp())
        await client.open("about:blank")
        await client.evaluate('''
            const a = document.createElement('a');
            a.id = 'dl-btn';
            a.href = 'data:text/plain;charset=utf-8,' + encodeURIComponent('CDP Download Integration Test');
            a.download = 'test_dl.txt';
            document.body.appendChild(a);
        ''')
        dl_res = await client.download("#dl-btn", dest_path=str(td))
        assert "completed successfully" in dl_res.lower()
        assert (td / "test_dl.txt").exists()
        assert (td / "test_dl.txt").read_text() == "CDP Download Integration Test"

        # 9. Test PDF Extraction
        print("\n9. Testing PDF Extraction...")
        pdf_res = await client.extract_pdf("https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf")
        assert "PDF Extracted" in pdf_res
        assert "Dummy PDF file" in pdf_res

        print("\nAll High-Level Built-in Tools PASSED!")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(run_test())

