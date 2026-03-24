"""
FedEx shipment tracker using Playwright.
Scrapes fedex.com/tracking — no API key needed.

Usage:
  python3 fedex_tracker.py <TRACKING_NUMBER>
Returns JSON: {"tracking": ..., "status": ..., "location": ..., "timestamp": ..., "delivered": ...}
"""
import asyncio
import json
import sys
from playwright.async_api import async_playwright

FEDEX_URL = "https://www.fedex.com/fedextrack/?tracknumbers={}"


async def track(tracking_number: str) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36"
        )
        page = await ctx.new_page()

        try:
            await page.goto(
                FEDEX_URL.format(tracking_number),
                wait_until="domcontentloaded",
                timeout=30000
            )
            # Wait for tracking content to load
            await page.wait_for_timeout(5000)

            # Try to get status from common FedEx selectors
            status = await _extract_text(page, [
                "[data-test-id='status-info'] span",
                ".shipment-status-heading",
                ".track-step--active .track-step__title",
                "h2.shipment-status",
                "[class*='StatusDescription']",
                "[class*='status-description']",
            ])

            location = await _extract_text(page, [
                "[data-test-id='location']",
                ".shipment-location",
                "[class*='LocationName']",
                "[class*='location-name']",
            ])

            timestamp = await _extract_text(page, [
                "[data-test-id='timestamp']",
                ".shipment-date",
                "[class*='Timestamp']",
                "[class*='event-date']",
            ])

            # Check if delivered
            page_text = await page.inner_text("body")
            delivered = any(word in page_text.upper() for word in [
                "DELIVERED", "PACKAGE DELIVERED"
            ])
            out_for_delivery = "OUT FOR DELIVERY" in page_text.upper()

            return {
                "tracking": tracking_number,
                "status": status or _parse_status_from_text(page_text),
                "location": location or "",
                "timestamp": timestamp or "",
                "delivered": delivered,
                "out_for_delivery": out_for_delivery,
                "raw_available": bool(status),
            }

        except Exception as e:
            return {
                "tracking": tracking_number,
                "status": "UNKNOWN",
                "location": "",
                "timestamp": "",
                "delivered": False,
                "out_for_delivery": False,
                "error": str(e),
            }
        finally:
            await browser.close()


async def _extract_text(page, selectors: list) -> str:
    for sel in selectors:
        try:
            el = await page.query_selector(sel)
            if el:
                text = await el.inner_text()
                if text and text.strip():
                    return text.strip()
        except Exception:
            continue
    return ""


def _parse_status_from_text(page_text: str) -> str:
    """Fallback: scan page text for known FedEx status phrases."""
    text_upper = page_text.upper()
    statuses = [
        "DELIVERED",
        "OUT FOR DELIVERY",
        "ON FEDEX VEHICLE FOR DELIVERY",
        "AT LOCAL FEDEX FACILITY",
        "IN TRANSIT",
        "DEPARTED FEDEX LOCATION",
        "ARRIVED AT FEDEX LOCATION",
        "SHIPMENT INFORMATION SENT TO FEDEX",
        "PICKED UP",
        "LABEL CREATED",
    ]
    for s in statuses:
        if s in text_upper:
            return s.title()
    return "IN TRANSIT"


def main():
    if len(sys.argv) > 1:
        tracking_number = sys.argv[1].strip()
    else:
        tracking_number = input("Enter FedEx tracking number: ").strip()

    result = asyncio.run(track(tracking_number))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
