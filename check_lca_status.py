"""
Check LCA case status on FLAG DOL portal.
Usage: python3 check_lca_status.py <CASE_NUMBER>
       python3 check_lca_status.py  (will prompt for case number)
Returns JSON: {"case": ..., "employer": ..., "title": ..., "date": ..., "status": ...}
"""
import asyncio
import json
import sys
from playwright.async_api import async_playwright

FLAG_URL = "https://flag.dol.gov/case-status-search"


async def check_status(case_number: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(FLAG_URL)
        await page.wait_for_timeout(2000)

        textarea = page.get_by_role("textbox")
        await textarea.fill(case_number)
        btn = page.get_by_role("button", name="Search")
        await btn.wait_for(state="visible")
        await page.wait_for_timeout(500)
        await btn.click()
        await page.wait_for_selector("table", timeout=20000)
        await page.wait_for_timeout(1000)

        rows = await page.query_selector_all("table tbody tr")
        result = None
        for row in rows:
            cells = await row.query_selector_all("td")
            if len(cells) >= 6:
                texts = [await c.inner_text() for c in cells]
                if case_number in texts[1]:
                    result = {
                        "case": texts[1],
                        "employer": texts[2],
                        "title": texts[3],
                        "date": texts[4],
                        "status": texts[5],
                    }
        await browser.close()
        return result


def main():
    if len(sys.argv) > 1:
        case_number = sys.argv[1].strip()
    else:
        case_number = input("Enter LCA case number (e.g. I-200-26075-123456): ").strip()

    result = asyncio.run(check_status(case_number))
    if result:
        print(json.dumps(result))
    else:
        print(json.dumps({"error": "Case not found", "case": case_number}))


if __name__ == "__main__":
    main()
