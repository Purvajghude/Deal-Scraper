import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from hermes import db
from hermes.api import app
from hermes.sources.coupons import CouponFeed, CouponSearch
from hermes import sources
from hermes.models import RawOpportunity


class OnlineTests(unittest.TestCase):
    def test_discovery_isolates_failed_sources(self):
        class Working:
            name = "working"
            async def fetch(self, client):
                return [RawOpportunity(title="Real coupon", url="https://example.com/coupon", source=self.name)]
        class Broken:
            name = "blocked"
            async def fetch(self, client):
                raise ValueError("Publisher blocked request")
        with patch.object(sources, "REGISTRY", [Working(), Broken()]), patch.object(sources, "coupon_sources", return_value=[]):
            items, errors = asyncio.run(sources.discover_all())
        self.assertEqual(len(items), 1)
        self.assertIn("blocked", errors)
        self.assertEqual(sources.SOURCE_STATUS["working"]["count"], 1)
        self.assertEqual(sources.SOURCE_STATUS["blocked"]["status"], "error")

    def test_public_dashboard_blocks_mutations(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(db, "DB_PATH", Path(directory) / "nested" / "hermes.db"), patch.dict(os.environ, {"HERMES_PUBLIC_READ_ONLY": "1", "HERMES_USERNAME": "", "HERMES_PASSWORD": ""}):
            client = TestClient(app)
            for route in ("/", "/health", "/api/status", "/api/sources", "/api/opportunities"):
                self.assertEqual(client.get(route).status_code, 200, route)
            for route in ("/api/refresh", "/api/watchlist", "/api/opportunities/1/dismissed"):
                self.assertEqual(client.post(route, json={}).status_code, 403, route)
            self.assertEqual(client.delete("/api/watchlist/1").status_code, 403)

    def test_optional_password_and_healthcheck(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(db, "DB_PATH", Path(directory) / "hermes.db"), patch.dict(os.environ, {"HERMES_USERNAME": "owner", "HERMES_PASSWORD": "test-only"}):
            client = TestClient(app)
            self.assertEqual(client.get("/").status_code, 401)
            self.assertEqual(client.get("/health").status_code, 200)
            self.assertEqual(client.get("/", auth=("owner", "test-only")).status_code, 200)
            self.assertEqual(client.get("/", headers={"Authorization": "Basic malformed"}).status_code, 401)

    def test_feed_parser_and_blocked_feed(self):
        async def run():
            xml = '''<rss version="2.0"><channel><title>Coupons</title><item><title>Save 20% &amp; free shipping</title><link>https://shop.example/coupon</link><description>&lt;b&gt;Code: SAVE20&lt;/b&gt;</description><pubDate>Mon, 12 Oct 2026 10:00:00 GMT</pubDate></item><item><title>Unsafe link</title><link>javascript:alert(1)</link></item></channel></rss>'''
            source = CouponFeed({"name": "Test", "url": "https://feed.example/rss", "region": "india"})
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, text=xml))) as client:
                items = await source.fetch(client)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].description, "Code: SAVE20")
            self.assertEqual(items[0].region_hint, "india")
            self.assertTrue(items[0].posted_at.startswith("2026-10-12"))
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(403))) as client:
                with self.assertRaises(httpx.HTTPStatusError):
                    await source.fetch(client)
        asyncio.run(run())

    def test_search_preserves_results_after_partial_failure(self):
        async def run():
            def respond(request):
                if request.url.params["q"] == "broken":
                    return httpx.Response(429)
                self.assertEqual(request.headers["X-Subscription-Token"], "test-only")
                return httpx.Response(200, json={"web": {"results": [{"title": "Coupon", "url": "https://merchant.example/promo", "description": "Code SAVE20"}]}})
            with patch.dict(os.environ, {"BRAVE_SEARCH_API_KEY": "test-only"}), patch("hermes.sources.coupons.load_profile", return_value={"discovery": {"coupon_queries": ["good", "broken"]}}):
                source = CouponSearch()
                async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
                    items = await source.fetch(client)
                self.assertEqual(len(items), 1)
                self.assertEqual(source.errors, {"broken": "Search HTTP 429"})
                self.assertEqual(items[0].source, "web_search/merchant.example")
        asyncio.run(run())

    def test_missing_search_key_makes_no_requests(self):
        async def run():
            with patch.dict(os.environ, {"BRAVE_SEARCH_API_KEY": ""}):
                async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: self.fail("Unexpected request"))) as client:
                    self.assertEqual(await CouponSearch().fetch(client), [])
        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
