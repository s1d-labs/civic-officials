"""Build platform_sites.csv: one row per urban local body site on a state's shared municipal platform.
Input: index pages saved in seeds/raw/ (read from India on 2026-11-09). Output columns match sites.csv.
Run: python seeds/build_platforms.py  (then run Setup)."""
import csv
import re
from pathlib import Path

RAW = Path(__file__).parent / "raw"
OUT = Path(__file__).parent.parent / "platform_sites.csv"
TN_MENU = {"about-us", "achievements", "acts-and-rules-documents", "amrut", "announcements", "atr-announcement", "awards-certiifcates",
           "combined-development-and-building-rules-2019", "comments", "contact-us", "covid-19", "elections", "engineering", "faqs", "feed",
           "finance", "fund-release", "government-orders", "insanitary-latrines", "judgements", "knmt", "list-of-municipality-websites-ulb-locator",
           "municipal-e-mail-ids", "namakku-naame-thittam", "nulm-addln", "planning", "policy-notes", "prevention-and-management-activities",
           "quick-links-2", "right-to-information-act", "roads", "sbm", "s-f-c", "smart-cities", "street-light", "ta", "tenders", "tenders-of-cma",
           "under-ground-drainage-scheme", "urban-e-governance", "water-supply", "whatsnew", "wp-content", "wp-includes", "wp-json", "ws"}


def read(name):
    return (RAW / name).read_text(errors="replace")


def rows():
    for host in sorted(set(re.findall(r"https?://([a-z0-9.-]+\.telangana\.gov\.in)", read("telangana-ulb-portals.html")))):
        if "municipality" in host or "corporation" in host:
            yield host, f"https://{host}/", host.split(".")[0], "TS", "Telangana"
    for slug in sorted(set(re.findall(r"tnurbantree\.tn\.gov\.in/([a-z0-9-]+)/", read("tamilnadu-list-of-municipality-websites.html"))) - TN_MENU):
        yield f"tnurbantree.tn.gov.in/{slug}", f"https://www.tnurbantree.tn.gov.in/{slug}/", slug, "TN", "Tamil Nadu"
    for sub in sorted(set(re.findall(r'subdomain\\u0022:\\u0022([a-z0-9-]+)\\u0022', read("assam-assamurban-ulb.html"))) - {"test", "www"}):
        yield f"{sub}.assamurban.in", f"https://{sub}.assamurban.in/", sub, "AS", "Assam"
    for path in sorted(set(re.findall(r'href="(?:\.\./)?(ulb/[A-Za-z0-9_]+/[A-Za-z0-9_]+\.aspx)"', read("jharkhand-udhd-home.html"), re.I))):
        name = path.split("/")[1]
        yield f"udhd.jharkhand.gov.in/{path.lower()}", f"https://udhd.jharkhand.gov.in/{path}", name, "JH", "Jharkhand"


def kerala():
    """Kerala's index is a PDF: addresses guessed from the 2025 ward-map body names, kept where the site answered (seeds/raw/kerala-found.txt)."""
    for line in read("kerala-found.txt").split():
        name, host = line.split("|")
        yield host, f"https://{host}/", name, "KL", "Kerala"


def main():
    seen, out = set(), []
    for domain, url, name, st, jur in list(rows()) + list(kerala()):
        if domain not in seen:
            seen.add(domain)
            out.append({"domain": domain, "url": url, "name": name, "kind": "Urban local body (platform)", "state_code": st, "jurisdiction": jur})
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["domain", "url", "name", "kind", "state_code", "jurisdiction"])
        w.writeheader()
        w.writerows(out)
    by = {}
    for r in out:
        by[r["jurisdiction"]] = by.get(r["jurisdiction"], 0) + 1
    print(len(out), by)


if __name__ == "__main__":
    main()
