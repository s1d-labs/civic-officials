"""News reports that name ward councillors of urban bodies with no official member list (owner, 2026-11-15: news names are
allowed where no official list exists, and every such row says clearly where it comes from). One queue item = one article:
payload {"kind": "form-news", "state", "url", "bodies": [{"lgd_code", "name"}] (the bodies the article is about)}.
Seeds: seeds/news_councillors.json (project civic-officials-councillors-news, GitHub runners, no proxy).

The page is saved once to the bucket (councillors/news/<sha1 of the url, 16 hex>.html.gz). One record per article,
"councillor-news:<sha1 16>" of type councillor_news_page: the publication (og:site_name or the JSON-LD publisher), the article
date (article:published_time or JSON-LD datePublished), the title, and the article text (JSON-LD articleBody, else the text
blocks of the <article> or <main> element). The names are read from that text on the box (civic-india/councillor_news.py),
never mixed with the official records: an official list of a body later replaces its news rows (sql/70).
A paywall, a login or a bot check ("Checking your browser", captcha) is never passed: the item ends with that reason and no
record."""
import gzip
import hashlib
import json
import re
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

import provenance

METHOD = "html page (news article text)"
BLOCKED = re.compile(r"checking your browser|just a moment\.\.\.|captcha|verify you are (a )?human|cf-chl-|subscribe to (continue|read)"
                     r"|sign in to (continue|read)|log ?in to continue|this content is for (subscribers|members)", re.I)


def _ld(soup):
    """NewsArticle-like objects of the page's JSON-LD blocks."""
    out = []
    for sc in soup.find_all("script", type="application/ld+json"):
        try:
            j = json.loads(sc.string or sc.get_text() or "")
        except Exception:
            continue
        stack = j if isinstance(j, list) else [j]
        while stack:
            x = stack.pop(0)
            if isinstance(x, list):
                stack.extend(x)
            elif isinstance(x, dict):
                if "@graph" in x:
                    stack.extend(x["@graph"] if isinstance(x["@graph"], list) else [x["@graph"]])
                if x.get("datePublished") or x.get("articleBody"):
                    out.append(x)
    return out


def _meta(soup, *names):
    for n in names:
        m = soup.find("meta", attrs={"property": n}) or soup.find("meta", attrs={"name": n}) or soup.find("meta", attrs={"itemprop": n})
        if m and m.get("content"):
            return m["content"].strip()
    return None


def article(html):
    """-> {"publication", "article_date", "title", "text", "text_from"} of a news page."""
    soup = BeautifulSoup(html, "lxml")
    ld = _ld(soup)
    pub = _meta(soup, "og:site_name")
    date = _meta(soup, "article:published_time", "datePublished", "publish-date", "pubdate")
    body = ""
    for x in ld:
        p = x.get("publisher")
        if not pub and isinstance(p, dict) and p.get("name"):
            pub = p["name"]
        date = date or x.get("datePublished")
        if isinstance(x.get("articleBody"), str) and len(x["articleBody"]) > len(body):
            body = x["articleBody"]
    title = _meta(soup, "og:title") or (soup.title.get_text(" ", strip=True) if soup.title else "")
    frm = "json-ld articleBody"
    if len(body) < 200:
        for t in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
            t.decompose()
        root = soup.find("article") or soup.find("main") or soup.body or soup
        blocks = [" ".join(b.get_text(" ").split()) for b in root.find_all(["p", "li", "td", "th", "h2", "h3", "h4"])]
        blocks = [b for b in blocks if b]
        txt = "\n".join(dict.fromkeys(blocks))
        if len(txt) > len(body):
            body, frm = txt, "page text blocks (" + root.name + ")"
    return {"publication": pub, "article_date": date, "title": title, "text": body.strip(), "text_from": frm}


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer (HTTP error or refused; see the run's http_<code> metrics)"
    a = article(r.text)
    title = re.search(r"<title[^>]*>([^<]*)", r.text[:20000], re.I)
    if (title and BLOCKED.search(title.group(1))) or (len(a["text"]) < 300 and BLOCKED.search(r.text[:20000])):
        return [], [], "bot check, login or paywall: skipped (never passed)"
    a["publication"] = a["publication"] or urlsplit(r.url or p["url"]).hostname
    key = hashlib.sha1(p["url"].encode()).hexdigest()[:16]
    path = f"councillors/news/{key}.html.gz"
    files = [(path, gzip.compress(r.content), "application/gzip")]
    if len(a["text"]) < 100:
        return [], files, "no article text"
    provenance.used()
    rec = {"type": "councillor_news_page", "source_kind": "news", "state": p["state"], "url": p["url"], "final_url": r.url,
           "bodies": p.get("bodies", []), "file": path, **a, **provenance.at(r, p["url"]), "method": METHOD}
    return [(f"councillor-news:{key}", rec)], files, ""
