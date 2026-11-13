"""Helpers of the ward3_* readers of Punjab, Haryana and Himachal corporations (branch ward-staff-northb).

rows(pages) reads a staff list PDF (pypdf layout text, _esw.pdf_pages) that has one row per person in the form
  [Sr. No.] Name   Designation-or-Area   [Phone]
where the gap between the name and the next column is the widest run of spaces on the row. Lines without a serial number (and
without a phone) under a row continue it: text that starts left of the row's second column goes to the name cell ("name_extra",
often the post when the second column names the ward or branch), the rest to the second cell ("mid_extra").
Word exports of numbered lists split the serial numbers ("12.   1" / "0" on the next line): such stray digits are dropped.
"""
import re

from dforms import _esw

PHONE_END = re.compile(r"\s{2,}((?:\+?91[\s-]?)?(?:0\d{2,4}[\s-]?\d{6,8}|[6-9]\d{4}[\s-]?\d{5}|[6-9]\d{9})"
                       r"(?:\s*[,/]\s*(?:0\d{2,4}[\s-]?\d{6,8}|[6-9]\d{4}[\s-]?\d{5}|[6-9]\d{9}))*)\s*$")
SERIAL = re.compile(r"^\s*(\d{1,3})\.?(?:\s+\d{1,2}(?=\s{2,}))?\s{2,}(?=\S)")
STRAY = re.compile(r"^\s{0,12}\d{1,2}(?=\s{3,}|\s*$)")


def lines_of(page):
    """The page's lines as the trail test splits them (form feeds count as line ends)."""
    return page.replace("\f", "\n").split("\n")


def split_gap(text, offset=0):
    """(left, right, x of right) of text split at its widest run of 3+ spaces; (text, "", None) when there is none."""
    best = None
    for m in re.finditer(r"\s{3,}", text):
        if best is None or len(m.group(0)) > len(best.group(0)):
            best = m
    if not best:
        return _esw.clean(text), "", None
    return _esw.clean(text[:best.start()]), _esw.clean(text[best.end():]), offset + best.end()


def rows(pages, skip=re.compile(r"(?i)^\s*(sr\.?\s*no|s\.?\s*no|name\b|municipal\s+corporation)"), post=None):
    """[dict(sr, name, mid, phone, name_extra, mid_extra, page, line, line_text)] of every numbered row of a staff list PDF.
    post: a regex of the first word of a post ("ASSISTANT|JUNIOR|..."); a row without a wide gap is cut where it matches."""
    out, cur = [], None
    for pn, pg in enumerate(pages, 1):
        for ln, raw in enumerate(lines_of(pg), 1):
            if not raw.strip() or skip.search(raw):
                continue
            m = SERIAL.match(raw)
            if m:
                rest = raw[m.end():]
                ph = PHONE_END.search(rest)
                phone = ph.group(1) if ph else ""
                body = rest[:ph.start()] if ph else re.sub(r"\s+-+\s*$", "", rest)     # "-" = no phone
                name, mid, x = split_gap(body, m.end())
                if not mid and post is not None:
                    pm = post.search(name)
                    if pm and pm.start() > 0:
                        x = m.end() + (len(body) - len(body.lstrip())) + pm.start()
                        name, mid = _esw.clean(name[:pm.start()]), _esw.clean(name[pm.start():])
                if not (mid or phone) and cur is not None:     # a stray serial digit before a continuation of the row above
                    t = raw[:m.start(1)] + " " * len(m.group(1)) + raw[m.start(1) + len(m.group(1)):]
                    for r in re.finditer(r"\S+(?:\s{1,2}\S+)*", t):
                        (cur["name_extra"] if r.start() < cur["x_mid"] - 6 else cur["mid_extra"]).append(_esw.clean(r.group(0)))
                    continue
                cur = {"sr": m.group(1), "name": name, "mid": mid, "phone": phone, "name_extra": [], "mid_extra": [],
                       "page": pn, "line": ln, "line_text": raw, "x_mid": x or (m.end() + len(body)), "x_name": m.end()}
                out.append(cur)
                continue
            if cur is None:
                continue
            t = STRAY.sub(lambda s: " " * len(s.group(0)), raw)
            ph = PHONE_END.search(t)
            if ph:
                cur["phone"] = ", ".join(x for x in (cur["phone"], ph.group(1)) if x)
                t = t[:ph.start()]
            for r in re.finditer(r"\S+(?:\s{1,2}\S+)*", t):
                txt = _esw.clean(r.group(0))
                if not txt:
                    continue
                (cur["name_extra"] if r.start() < cur["x_mid"] - 6 else cur["mid_extra"]).append(txt)
    for r in out:
        r["name_extra"] = " ".join(r["name_extra"])
        r["mid_extra"] = " ".join(r["mid_extra"])
    return out
