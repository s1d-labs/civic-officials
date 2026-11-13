"""Shared helpers of the fork-E police readers (dforms/police3_as.py, police3_od.py, police3_wb.py ...). Not a reader itself.

kind(text) -> (level, office_type, post) for one office or station label as published ("O.C. Nagaon P.S.", "I/C Traffic",
"Addl.SP(HQ) Office", "Police Control Room & Broad Band", "Cyber P.S.", "All Women P.S.", "ACP (Jalukbari)").
station_name(text) -> the station or post name without the officer prefix ("O.C. Nagaon P.S." -> "Nagaon P.S.").
"""
import re

from dforms._police import clean

OFFICER = re.compile(r"^\s*(?:O\.?\s?/?\s?C\.?|I\.?\s?/\s?C\.?|I\.?C\.?|IIC|Incharge|In-?charge|Officer[- ]in[- ]charge(?: of)?)\s*[,.:-]?\s+",
                     re.I)
STATION = re.compile(r"\bP\.?\s?S\b\.?|police station|\bthana\b", re.I)
POST = re.compile(r"\b(?:O\.?\s?P|T\.?O\.?P|P\.?\s?P|B\.?O\.?P|Out\s?-?post|Police Post|Patrol Post|Beat House|B\.?H)\b\.?", re.I)
WOMEN = re.compile(r"\bwomen\b|\bmahila\b|\bW\.?P\.?S\b", re.I)
CYBER = re.compile(r"\bcyber\b|\bCDR\b|internet", re.I)
TRAFFIC = re.compile(r"\btraffic\b|\bT\.?I\.?\b(?=\s|$)", re.I)
CONTROL = re.compile(r"control\s*room|\bP\.?C\.?R\b|\b(?:100|112)\s*dial|dial\s*(?:100|112)|\bERSS\b|\bVHF\b", re.I)
DISTRICT = re.compile(r"\b(?:S\.?S\.?P|S\.?P|Addl\.?\s*S\.?P|ASP|Superintendent|Supdt|C\.?P|Jt\.?\s*C\.?P|Joint Commissioner|"
                      r"Commissioner|D\.?C\.?P|Addl\.?\s*D\.?C\.?P|DIG|DIGP|IGP?)\b", re.I)
SUBDIV = re.compile(r"\b(?:SDPO|S\.D\.P\.O|Dy\.?\s*S\.?P|DSP|Sub[- ]?Divisional)\b", re.I)
CIRCLE = re.compile(r"^\s*(?:CI|C\.I\.?|ACP|A\.C\.P\.?|Circle Inspector)\b", re.I)
RESIDENCE = re.compile(r"\bresi(?:dence|dnece)?\b|\(R\)", re.I)


def station_name(text):
    """'O.C. Nagaon P.S.' -> 'Nagaon P.S.'; 'I/C Haiborgaon TOP' -> 'Haiborgaon TOP'; 'Dharamtul PS' -> 'Dharamtul PS'."""
    t = clean(text) or ""
    t = OFFICER.sub("", t)
    return t.strip(" ,.-") or None


def kind(text):
    """(level, office_type, post) of a published label. post = the officer prefix when there is one ('O.C.', 'I/C')."""
    t = clean(text) or ""
    m = OFFICER.match(t)
    post = clean(m.group(0)).strip(" ,.:-") if m else None
    rest = t[m.end():] if m else t
    if RESIDENCE.search(t):
        return "district", "residence", post
    if CONTROL.search(t):
        return "district", "control room", post
    if STATION.search(rest) and not re.search(r"\bcyber\b", rest, re.I):
        if WOMEN.search(rest):
            return "police_station", "women police station", post or "Officer in charge"
        return "police_station", "police station", post or "Officer in charge"
    if re.search(r"\bcyber\b", rest, re.I) and STATION.search(rest):
        return "police_station", "cyber police station", post or "Officer in charge"
    if POST.search(rest) and not DISTRICT.search(rest):
        return "police_station", "police post", post or "In-charge"
    if CYBER.search(t):
        return "district", "cyber", post
    if TRAFFIC.search(t):
        return "district", "traffic", post
    if WOMEN.search(t):
        return "district", "women", post
    if CIRCLE.match(rest):
        return "circle", "circle", post
    if SUBDIV.search(t):
        return "subdivision", "subdivision", post
    if DISTRICT.search(t):
        return "district", "office", post
    return "district", "unit", post


def norm_station(s):
    """Key to compare a station name with civic.police_station names: lower case, no 'police station' / 'P.S.' / 'O.P.' words."""
    s = (clean(s) or "").lower()
    s = OFFICER.sub("", s)
    s = re.sub(r"\bpolice\s+(station|out\s?post|outpost|post|patrol post)\b|\bp\.?\s?s\b\.?|\bthana\b|\bo\.?\s?p\b\.?|\bt\.?o\.?p\b|"
               r"\bp\.?p\b|\bsadar\b|\(.*?\)", " ", s)
    return re.sub(r"[^a-zऀ-෿]+", "", s)
