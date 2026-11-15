"""cforms/news.py on small made-up pages (no network)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cforms import news  # noqa: E402


class R:
    def __init__(self, text, url="https://example.com/a"):
        self.text, self.url, self.content = text, url, text.encode()


LD = {"@context": "https://schema.org", "@type": "NewsArticle", "datePublished": "2026-02-27T10:00:00+05:30",
      "publisher": {"@type": "Organization", "name": "Example News"}, "articleBody": "Ward 1: A Kumar (BJP). " * 20}


def test_ld_article():
    html = f'<html><head><title>Results</title><script type="application/ld+json">{json.dumps(LD)}</script></head><body></body></html>'
    recs, files, why = news.fetch({"url": "https://example.com/a", "state": "JH", "bodies": [{"lgd_code": "1", "name": "X"}]},
                                  lambda u: R(html))
    assert why == "" and len(recs) == 1 and files[0][0].startswith("councillors/news/")
    d = recs[0][1]
    assert d["publication"] == "Example News" and d["article_date"].startswith("2026-02-27") and d["source_kind"] == "news"
    assert d["text"].startswith("Ward 1: A Kumar")


def test_text_blocks_and_host_fallback():
    body = "".join(f"<p>Ward No. {i}: Name {i} won the seat by many votes in the town.</p>" for i in range(1, 8))
    html = f"<html><head><title>Town poll</title></head><body><nav>menu</nav><article>{body}</article></body></html>"
    recs, _, why = news.fetch({"url": "https://news.example.org/x", "state": "UP"}, lambda u: R(html, "https://news.example.org/x"))
    assert why == "" and recs[0][1]["publication"] == "news.example.org" and "menu" not in recs[0][1]["text"]


def test_bot_check_skipped():
    html = "<html><head><title>Checking your browser...</title></head><body>wait</body></html>"
    recs, files, why = news.fetch({"url": "https://example.com/b", "state": "JH"}, lambda u: R(html))
    assert not recs and not files and why.startswith("bot check")
