"""Sikkim: the heads of the urban bodies, from district portal tables (dforms/_ulb2_ne.py reads them).

- Gangtok, https://gangtokdistrict.nic.in/list-of-officers/ (S3WaaS, Election Cell "LIST OF OFFICERS", saved by archive.s1d.me
  2026-11-10): EROs and AEROs of the Municipality Election 2026 with name, designation and contact number. Kept: the Municipal
  Commissioner, Deputy, Joint and Assistant Commissioners of Gangtok Municipal Corporation ("..., GMC") and the MEO (Municipal
  Executive Officer) of Singtam. The page writes "MUNICIPAL COMMISSINER" and "MEO": the rule sets role head (role_from "rule").
- Namchi, https://namchi.nic.in/contact-directory-2/ (S3WaaS contact directory, saved 2026-11-06): row "MEO, Namchi Municipal
  Council" (Ms. Yogen Syanden, 257157/9593375861).
Not used: Gyalshing's /departments/ and /helpline/ pages name an "MEO" of "Urban Dev & Housing" with two different names on the
same day (Shri Gopal Sharma, 9733122686; Shri D.R. Thapa, 8372038917) and do not name the Nagar Panchayat. Soreng's pages name no
person. Pakyong district (Pakyong, Rangpo) has no site in the archive. udhdsikkim.org (the department's site, linked from the
district pages) does not resolve (2026-11-11). Elected heads: a municipal election is under way in 2026 (electoral rolls published
by the district sites); no result page was found.
Not India-only.
"""
from dforms import _ulb2_ne

MODULE = "ulb2_sk"
STATE = "SK"
GMC = ("Gangtok", "249694", "Municipal Corporation")
PAGES = [
    {"url": "https://gangtokdistrict.nic.in/list-of-officers/", "district": "Gangtok", "key": "gangtok-officers",
     "rules": [[r"^municipal\s+commiss\w*,?\s*GMC\b", *GMC, "head"],
               [r"^(deputy|joint|assistant|addl\.?|additional)\s+commis\w*,?\s*GMC\b", *GMC, "deputy"],
               [r"^MEO\s*,?\s*Singtam\b", "Singtam", "249695", "Nagar Panchayat", "head"]]},
    {"url": "https://namchi.nic.in/contact-directory-2/", "district": "Namchi", "key": "namchi-directory",
     "rules": [[r"^MEO\s*,?\s*Namchi\s+Municipal\s+Council", "Namchi", "249692", "Municipal Council", "head"]]},
]


def items(get=None):
    return [{"key": f"{MODULE}-{p['key']}", "payload": {"reader": MODULE, "url": p["url"], "district": p["district"], "state": STATE,
                                                       "rules": p["rules"], "india_only": False}} for p in PAGES]


def parse(html, rules, district=None, url=""):
    return _ulb2_ne.parse(MODULE, STATE, html, rules, district, url)


def fetch(p, get):
    return _ulb2_ne.fetch(MODULE, STATE, p, get)
