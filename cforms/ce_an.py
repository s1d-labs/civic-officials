"""Andaman and Nicobar Islands: ward councillors of Sri Vijaya Puram (Port Blair) Municipal Council, the only urban body of
the islands (24 wards, 3 nominated members), from the council's RTI section 4(1)(b) disclosure.

pbmc.gov.in/files?id=1023&websection=RTI is a 27-page PDF with a text layer (PDF24, 28.02.2025). Item (viii) lists the
Chairperson, Sr Vice Chairperson and Junior Vice Chairperson, five sub-committees, then "Ward Councillors": a table
S No | Name of Elected Representatives | Ward No | Designation, one line per ward (24). The text is read with pdftotext
-layout (poppler; installed on a GitHub runner when missing). The posts of the chair and the vice chairs go to the
councillor of that name. The site answers from outside India (archive.s1d.me pool copies).
One queue item = the file. Record id councillor:AN:sri-vijaya-puram-mc:<ward no>.
"""
import re
import shutil
import subprocess
import tempfile

METHOD = 'pdf text (pdftotext -layout)'     # source trail (provenance.py): how this reader reads its sources

URL = "https://pbmc.gov.in/files?id=1023&websection=RTI"
BODY, LGD = "Sri Vijaya Puram (Port Blair) Municipal Council", "253098"
ELECTION = "Sri Vijaya Puram Municipal Council (as listed in its RTI 4(1)(b) disclosure of 28.02.2025)"
POSTS = ("Chairperson", "Sr Vice Chairperson", "Junior Vice Chairperson")


def tools():
    if shutil.which("pdftotext"):
        return True
    cmd = "sudo -n apt-get update -q && sudo -n apt-get install -y -q poppler-utils"
    return subprocess.run(cmd, shell=True, capture_output=True).returncode == 0 and bool(shutil.which("pdftotext"))


def bare(name):
    return re.sub(r"^(Shri|Smti|Smt|Sri|Mr|Mrs|Ms|Dr)\.?\s+", "", name.strip(), flags=re.I).lower()


def parse(text, url=URL):
    posts, cur = {}, None
    head = text.split("Ward Councillors", 1)
    if len(head) < 2:
        return []
    for ln in head[0].splitlines()[-200:]:
        t = ln.strip()
        if t in POSTS:
            cur = t
            continue
        m = re.match(r"\d+\.\s+(.+?)\s*$", t)
        if cur and m:
            posts[bare(m.group(1))] = cur
            cur = None
    recs = []
    for ln in head[1].splitlines():
        m = re.match(r"\s*(\d+)\.?\s+(.+?)\s{2,}(\d{1,2})\s+(Councillor|Member)\b", ln)
        if not m:
            if recs and re.search(r"\(ix\)|directory of its officers", ln):
                break
            continue
        ward = str(int(m.group(3)))
        name = " ".join(m.group(2).split())
        d = {"type": "councillor", "state": "AN", "body": BODY, "lgd_code": LGD, "ward_no": ward, "name": name,
             "position": posts.get(bare(name), "Councillor"), "election": ELECTION, "url": url}
        recs.append((f"councillor:AN:sri-vijaya-puram-mc:{ward}", d))
    return recs


def fetch(p, get):
    if not tools():
        return [], [], "poppler not available"
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    if not r.content.startswith(b"%PDF"):
        return [], [], "not a PDF"
    files = [("councillors/AN/svpmc-rti-4-1-b.pdf", r.content, "application/pdf")]
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(r.content)
        f.flush()
        text = subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, text=True).stdout
    recs = parse(text, p.get("url", URL))
    return recs, files, "" if recs else "no councillor table"
