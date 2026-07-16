from __future__ import annotations

import os
from typing import Any
from xml.etree import ElementTree

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]

_DEFAULT_RSS = "https://feeds.bbci.co.uk/news/rss.xml"
_FALLBACK_HEADLINES = [
    "AI assistant NICO is now fully operational",
    "Raspberry Pi performance improvements announced",
    "Open-source community celebrates new milestone",
]


class NewsTool:
    """Fetches top headlines from a configurable RSS feed.

    Defaults to BBC News RSS when no ``NEWS_RSS_URL`` is set.
    Falls back to hardcoded demo headlines when offline.
    """

    name = "news"
    description = "Get the latest news headlines from an RSS feed"
    category = "web"
    timeout_seconds = 10.0
    max_retries = 1
    parameters = {
        "type": "object",
        "properties": {
            "count": {
                "type": "integer",
                "description": "Number of headlines to return (default 5, max 10)",
            },
            "rss_url": {
                "type": "string",
                "description": "Custom RSS feed URL (optional)",
            },
        },
    }

    def __init__(self, rss_url: str | None = None) -> None:
        self.rss_url = rss_url or os.getenv("NEWS_RSS_URL", _DEFAULT_RSS)

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        count: int = min(int(kwargs.get("count", 5)), 10)
        url: str = str(kwargs.get("rss_url", self.rss_url))

        if httpx is None:
            return self._stub(count)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    follow_redirects=True,
                    timeout=8.0,
                    headers={"User-Agent": "NICO-AI-Assistant/1.0"},
                )
                response.raise_for_status()
                headlines = self._parse_rss(response.text, count)
                return {
                    "source": url,
                    "count": len(headlines),
                    "headlines": headlines,
                }
        except Exception as exc:
            stub = self._stub(count)
            stub["error"] = f"RSS fetch failed: {exc}"
            stub["source"] = url
            return stub

    def _parse_rss(self, xml_text: str, count: int) -> list[dict[str, str]]:
        """Parse RSS XML and return a list of headline dicts."""
        headlines: list[dict[str, str]] = []
        try:
            root = ElementTree.fromstring(xml_text)
            # Handle both <rss> and Atom feeds
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            items = root.findall(".//item") or root.findall(".//atom:entry", ns)
            for item in items[:count]:
                title_el = item.find("title") or item.find("atom:title", ns)
                link_el = item.find("link") or item.find("atom:link", ns)
                desc_el = item.find("description") or item.find("atom:summary", ns)

                title = (
                    title_el.text if title_el is not None else "No title"
                )
                link = (
                    link_el.text or link_el.get("href", "")
                    if link_el is not None
                    else ""
                )
                desc = (
                    desc_el.text[:200] if desc_el is not None and desc_el.text else ""
                )

                headlines.append(
                    {
                        "title": (title or "").strip(),
                        "link": (link or "").strip(),
                        "summary": desc.strip(),
                    }
                )
        except ElementTree.ParseError:
            pass
        return headlines

    @staticmethod
    def _stub(count: int) -> dict[str, Any]:
        return {
            "source": "offline",
            "count": min(count, len(_FALLBACK_HEADLINES)),
            "headlines": [
                {"title": h, "link": "", "summary": ""}
                for h in _FALLBACK_HEADLINES[:count]
            ],
        }
