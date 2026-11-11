"""Shared helpers for the state lists of urban body officials (dforms/ulb_<xx>.py): one list per state from the Directorate of
Municipal Administration / Urban Development that names the head (EO / CMO / Commissioner / Chief Officer) and often the
chairperson or mayor of every town body of the state.

record() builds one "dept:ulb_<xx>:<key>" dept_office record: dept "town_body", level "body", area = the body's own name exactly as
the list writes it (civic-india sql/86 and sql/87 tie it to civic.ulb by name in the district, or in the state when the list
gives no district). Extra keys: body_type (as the list writes it, e.g. "Nagar Palika Parishad"), lgd_code / census_code when the
list gives one, role ("head", "chair", "deputy", "member", "staff" from role_of(post)).
"""
import re

from dforms import _esw

# the post that runs the body (appointed head), the elected head, their deputies, and elected ward members. Order: member, deputy and
# chair words before head words ("Ward Commissioner" is a councillor in Assam and Bengal; "Deputy Commissioner" a deputy).
# A deputy is a deputy OF THE HEAD: "Assistant Engineer" or "Junior Assistant" is staff.
# Devanagari words stand outside \b: vowel signs are not \w, so \b does not hold after them.
_HEADS = r"(municipal\s*|city\s*|nagar\s*)?(commissioner|executive\s*officer|e\.?\s?o\b|chief\s*officer|municipal\s*officer|secretary|mayor|chair|president|administrator)"
ROLES = (
    ("member", r"\b(ward\s*(commissioner|member|councill?or)|councill?or|corporator|parshad|sabhasad|nagar\s*sevak)\b|पार्षद|सभासद|नगरसेवक"),
    ("deputy", r"\b(vice|up\s*-?\s*(mahapaur|adhyaksh|sabhapati)|upa\s*-?\s*(mahapaur|adhyaksh))\b|"
               r"\b(deputy|dy\.?|additional|addl\.?|add\.|joint|asst\.?|assistant)\s*" + _HEADS +
               r"|^उप|\sउप|सहायक\s*नगर\s*आयुक्त|अपर\s*नगर\s*आयुक्त"),
    ("chair", r"\b(mayor|chair\s*-?\s*(man|person|woman)?|president|adhyaksh|adhyaksha|sabhapati|mahapaur|nagar\s*pramukh|pramukh"
              r")\b|मेयर|महापौर|अध्यक्ष|सभापति|नगराध्यक्ष"),
    ("head", r"\b(commissioner|executive\s*officer|e\.?\s?o\.?|chief\s*officer|c\.?\s?o\.?|chief\s*municipal\s*officer|c\.?\s?m\.?\s?o\.?|"
             r"c\.?\s?e\.?\s?o\.?|chief\s*executive(\s*officer)?|administrator|secretary|mukhya\s*nagar\s*palika\s*adhikari|adhishasi\s*adhikari|town\s*clerk"
             r")\b|आयुक्त|अधिशासी\s*अधिकारी|अधि[0०.]\s*अधिकारी|मुख्य\s*नगर\s*पालिका\s*अधिकारी|मुख्याधिकारी|कार्यपालक\s*पदाधिकारी"),
)


def role_of(post):
    """head / chair / deputy / member / staff from the post text ("Executive Officer" -> head, "Chairman" -> chair, "Vice Chairman" ->
    deputy, "Ward Commissioner" -> member, "Assistant Engineer" -> staff)."""
    p = (post or "").lower()
    for role, rx in ROLES:
        if re.search(rx, p):
            return role
    return "staff"


def record(module, state, body, post, seen, name="", phone="", email="", district=None, body_type=None, source="", latin=None, **extra):
    """(record id, data) for one post of one body. seen: a set of keys already used in this answer (keeps ids unique).
    latin: a Latin form of the body name for the ids, when the list writes the name in another script (_esw.slug keeps only
    a-z0-9, so two Hindi bodies would get the same id)."""
    from dforms._water import unique
    body = _esw.clean(body)
    post = _esw.clean(post)
    bk = _esw.slug(latin or body)
    key = unique(f"{state}-{_esw.slug(district or '')}-{bk}-{_esw.slug(post) or 'office'}", seen)
    return _esw.record(module, key, dept="town_body", level="body", area=body, post=post, name=_esw.clean(name),
                       phone=_esw.phones(phone) if phone else "", email=_esw.emails(email) if email else "", state=state,
                       district=_esw.clean(district) or None, body_type=_esw.clean(body_type) or None, role=role_of(post),
                       office_id=f"{state}-ULB-{_esw.slug(district or '')}-{bk}", source=source, **extra)
