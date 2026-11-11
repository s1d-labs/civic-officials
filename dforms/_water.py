"""Shared helpers for the water readers (dforms/water_*.py): the level of an office from the post that heads it.

level_of("Executive Engineer, PH Dn., Kottayam") -> "division". Order matters: AEE / AEN (sub-division) before EE, EE before SE, SE
before CE (zone when a region is named, else state), so "EE & TA to SE" stays a division post and "S.E. O/o ACE" a circle post.
"""
import re

LEVELS = (
    ("subdivision", r"\bA\.?\s?E\.?\s?E\b|\bA\.?\s?EN\b|\bAEN\b|ASS(?:IS)?T(?:AN)?T\.?\s*EXEC|ASSISTANT\s+EXECUITVE|\bS\.?\s?D\.?\s?[OE]\b"
                    r"|SUB[\s.-]*D(?:IV|N)|\bDY\.?\s*ENG|DEPUTY\s+ENGINEER|\bAEE\b"),
    ("division", r"\bE\.?\s?E\b|EXECUTIVE\s+ENGINEER|\bDIVISION\b|\bDN\b\.?|\bDIVN?\b"),
    ("circle", r"\bS\.?\s?E\b|SUPERINTEND(?:ING|ENT)|SUPDT\.?\s*ENG|\bCIRCLE\b"),
    ("zone", r"\bA\.?\s?C\.?\s?E\b|ADDL\.?\s*C\.?\s?E|ADDITIONAL\s+CHIEF|\bZONE\b|\bREGION\b|\bREG\.|\bRZ\b"),
    ("section", r"\bA\.?\s?E\b|ASSISTANT\s+ENGINEER|\bSECTION\b|\bSN\b\.?|\bJ\.?\s?E\b|JUNIOR\s+ENGINEER|SERVICE\s+STATION"),
    ("state", r"CHIEF\s+ENGINEER|ENGINEER[\s-]+IN[\s-]+CHIEF|\bE\.?\s?I\.?\s?C\b|\bC\.?\s?E\b|MANAGING\s+DIRECTOR|SECRETARY"),
)


def level_of(post, default="state"):
    p = (post or "").upper()
    for level, rx in LEVELS:
        if re.search(rx, p):
            return level
    return default


def area_after(post):
    """The place part of a post: "Executive Engineer, PH Dn., Kottayam" -> "PH Dn., Kottayam"; "" when there is none."""
    parts = re.split(r"\s*,\s*", post or "", maxsplit=1)
    return parts[1].strip(" ,") if len(parts) == 2 else ""


def unique(key, seen):
    k, i = key, 2
    while k in seen:
        k, i = f"{key}:{i}", i + 1
    seen.add(k)
    return k
