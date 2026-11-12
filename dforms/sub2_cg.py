"""Chhattisgarh: tahsildars, additional and naib tahsildars and SDOs (Revenue) of every district, with mobiles, from the officer search
of the Revenue & Disaster Management Department (revenue.cg.nic.in/RevenueOfficerSearchPage.aspx, run by NIC Chhattisgarh). Answers
only from India (this box in Germany is refused).

The page is an ASP.NET form: district (ddlDistrict, 33 site ids) -> postback -> post list (ddlDesignation: 004 SDO (Revenue),
005 SDM, 008 Tahsildar, 009 Additional Tahsildar, 010 Naib Tahsildar, and district/state posts not read here) -> postback -> one
table GridView1 (No, Post with place, Name, Mobile). The post cell names the court and the place in Hindi: "न्यायालय तहसीलदार, आरंग",
"न्यायालय अतिरिक्त तह्सीलदार आरंग", "अनुविभागीय अधिकारी (रा.) तिलदा-नेवरा". The page shows no date.

One queue item per district: 1 GET + 1 POST (district) + 5 POSTs (one per post), all with the hidden fields of the page before.
Area = the LGD sub-district name when the Hindi place matches one of the district (TAHSILS: Hindi names from lgd.blocks,
lgd.villages and lgd.urban_local_bodies of DB civic, 231 of 252 sub-districts), else a Latin spelling of the Hindi place;
area_regional = the place as the site writes it. Record ids: dept:sub2_cg:CG-<site district id>-<post code>-<slug of area>[:n].
"""
import difflib
import re

from dforms import _esw

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "sub2_cg"
URL = "https://revenue.cg.nic.in/RevenueOfficerSearchPage.aspx"
# post code on the site -> (post, dept, level)
POSTS = {"004": ("Sub-Divisional Officer (Revenue)", "administration", "subdivision"),
         "005": ("Sub-Divisional Magistrate", "administration", "subdivision"),
         "008": ("Tahsildar", "revenue", "subdistrict"),
         "009": ("Additional Tahsildar", "revenue", "subdistrict"),
         "010": ("Naib Tahsildar", "revenue", "subdistrict")}
# site district id -> (LGD district code, LGD district name)
DISTRICTS = {"57": ("382", "Kabeerdham"), "60": ("381", "Uttar Bastar Kanker"), "49": ("643", "Kondagaon"), "55": ("383", "Korba"),
             "53": ("384", "Korea"), "67": ("759", "Khairagarh-Chhuikhadan-Gandai"), "51": ("645", "Gariyaband"),
             "66": ("734", "Gaurela-Pendra-Marwahi"), "56": ("380", "Jashpur"), "54": ("379", "Janjgir-Champa"),
             "61": ("376", "Dakshin Bastar Dantewada"), "43": ("378", "Durg"), "59": ("377", "Dhamtari"), "46": ("637", "Narayanpur"),
             "52": ("650", "Bemetara"), "65": ("649", "Balrampur-Ramanujganj"), "50": ("644", "Balodabazar-Bhatapara"),
             "45": ("374", "Bastar"), "62": ("646", "Balod"), "40": ("375", "Bilaspur"), "47": ("636", "Bijapur"), "63": ("647", "Mungeli"),
             "71": ("760", "Manendragarh-Chirmiri-Bharatpur(M C B)"), "58": ("385", "Mahasamund"),
             "68": ("761", "Mohla-Manpur-Ambagarh Chouki"), "42": ("388", "Rajnandgaon"), "41": ("386", "Raigarh"), "44": ("387", "Raipur"),
             "69": ("762", "Sakti"), "48": ("642", "Sukma"), "39": ("389", "Surguja"), "64": ("648", "Surajpur"),
             "70": ("763", "Sarangarh-Bilaigarh")}
TAHSILS = {
    "374": {'Bakavand': [], 'Bastanar': ['बसतानार', 'बस्तानर'], 'Bastar': ['बस्तर'], 'Bhanpuri': ['भनपुरी'], 'Darbha': ['दरभा'], 'Jagdalpur': ['जगदलपुर', 'जगदलपूर'], 'Karpawand': ['करपावड'], 'Lohandiguda': ['लोहंडीगुडा', 'लोहान्दिगुदा'], 'Nangur': ['नानगुर'], 'Tokapal': ['टोका पाल', 'तोकापाल']},
    "375": {'Belgahna': ['बेलगहना'], 'Beltara': ['बेलतरा'], 'Bilaspur': ['बिलासपुर'], 'Bilha': ['बिल्हा'], 'Bodri': ['बोडरी', 'बोदरी'], 'Kota': ['कोटा'], 'Masturi': ['मस्तुरी'], 'Pachpedi': ['पचपेडी'], 'Ratanpur': ['रतनपुर'], 'Sankari': [], 'Seepat': ['सीपत'], 'Takhatpur': ['तखतपुर']},
    "376": {'Bade Bacheli': ['बड़े बचेली'], 'Barsur': ['बारसूर'], 'Dantewada': ['दंतेवाडा'], 'Gidam': ['गीदम'], 'Katekalyan': ['कटेकल्याण'], 'Kuakonda': ['कुवाकोंदा']},
    "377": {'Belargaon': ['बेलरगाँव'], 'Bhakhara': ['भखारा', 'भाखरा'], 'Dhamtari': ['धमतरी'], 'Kukrel': ['कुकरेल'], 'Kurud': ['कुरूद'], 'Magarlod': ['मगरलोड'], 'Nagri': ['नगरी']},
    "378": {'Ahiwara': ['अहिवारा'], 'Bhilai-3': ['भिलाई 3', 'भिलाई नगर'], 'Bori': [], 'Dhamdha': ['धमधा'], 'Durg': ['दुर्ग'], 'Patan': ['पाटन']},
    "379": {'Akaltara': ['अकलतरा'], 'Baloda': ['बलोदा'], 'Bamhnidih': ['बम्हनीडीह'], 'Champa': ['चाम्पा'], 'Janjgir': ['जांजगीर'], 'Nawagarh': ['नवागढ़'], 'Pamgarh': ['पामगढ़', 'पामगढ़'], 'Saragaon': ['सारागाँव', 'सारागांव'], 'Shivrinarayan': ['शिवरीनारायण']},
    "380": {'Bagbahar': ['बागबहार'], 'Bagicha': ['बगीचा', 'बागीचा'], 'Duldula': ['दुलदुला'], 'Farsabahar': [], 'Jashpur': ['जशपुर'], 'Kansabel': ['कांसाबेल'], 'Kunkuri': ['कुनकुरी'], 'Manora': ['मनोरा'], 'Pathalgaon': ['पथलगांव'], 'Sanna': ['सन्ना'], 'Tapkara': ['तपकरा']},
    "381": {'Aamabeda': [], 'Antagarh': ['अंतागढ़'], 'Bande': ['बन्दे'], 'Bhanupratappur': ['भानुप्रतापपुर'], 'Charama': ['चारामा', 'चारामाँ'], 'Durgkondal': ['दुर्गकोंडल'], 'Kanker': ['कांकेर'], 'Koylibeda': [], 'Narharpur': ['नरहरपुर', 'नरहरपूर'], 'Pakhanjur': [], 'Sarona': ['सरोना']},
    "382": {'Bodla': ['बोडला'], 'Kawardha': ['कवर्धा'], 'Kukdur': ['कूकदुर'], 'Kunda': ['कुंडा'], 'Pandariya': ['पंडरिया'], 'Pipariya': ['पिपरिया'], 'Rengakharkala': [], 'Sahaspur Lohara': ['सहसपुर लोहारा', 'सहसपुर-लोहारा']},
    "383": {'Ajgarbahar': ['अजगरबहार'], 'Barpali': ['बरपाली'], 'Bhaisma': ['भैसमा'], 'Darri': [], 'Dipka': ['दीपका'], 'Hardibazar': ['हरदीबाज़ार'], 'Kartala': ['करतला'], 'Katghora': ['कटघोरा'], 'Korba': ['कोरबा'], 'Pali': ['पाली'], 'Pasan': ['पासन'], 'Poundi-Uproda': []},
    "384": {'Baikunthpur': ['बैकुंठपुर', 'बैकुंठपूर'], 'Patna': ['पटना'], 'Pondi(Bachra)': ['पोंडी'], 'Sonhat': ['सोनहत']},
    "385": {'Bagbahra': [], 'Basna': ['बसना'], 'Komakhan': ['कोमाखान'], 'Mahasamund': ['महासमुंद'], 'Pithora': ['पिथोरा'], 'Saraipali': ['सरईपाली', 'सरईपाली (भागता)', 'सराईपाली']},
    "386": {'Chhal': ['छाल'], 'Dharamjaigarh': ['धरमजयगढ़', 'धरमजैगढ़'], 'Gharghoda': ['घरघोड़ा'], 'Kapu': ['कापू'], 'Kharsia': ['खरसिया'], 'Lailunga': ['लैलूंगा'], 'Mukdega': ['मूकडेगा'], 'Pusour': ['पुसौर'], 'Raigarh': ['रायगढ़'], 'Tamnar': ['तमनार']},
    "387": {'Abhanpur': ['अभनपुर'], 'Arang': ['आरंग'], 'Dharsiwa': ['धरसीवा'], 'Gobra Nawapara': ['गोबर नवापारा', 'गोबरा नवापारा'], 'Kharora': ['खरोरा'], 'Mandir Hasoud': [], 'Raipur': ['रायपुर'], 'Tilda': ['तिल्दा']},
    "388": {'Chhuriya': ['छुरिया'], 'Dongargaon': ['डोंगरगांव'], 'Dongargarh': ['डोंगरगढ़'], 'Ghumka': ['घुमका'], 'Kumarda': ['कुमरदा'], 'Lal Bahadur Nagar': ['लाल बहादुर नगर'], 'Rajnandgaon': ['राजनांदगांव']},
    "389": {'Ambikapur': ['अंबिकापुर'], 'Batouli': [], 'Darima': ['दरिमा'], 'Lakhanpur': ['लखनपुर'], 'Lundra': ['लुन्द्रा'], 'Mainpat': ['मैनपाट'], 'Sitapur': ['सीतापुर'], 'Udaypur': []},
    "636": {'Bhairamgarh': ['भैरमगढ़'], 'Bhopalpattnam': ['भोपालपट्टनम'], 'Bijapur': ['बीजापुर'], 'Gangaloor': ['गंगालूर'], 'Kutru': ['कुतरू'], 'Usur': ['उसूर']},
    "637": {'Chhotedongar': ['छोटेडोंगर'], 'Kohkameta': [], 'Narayanpur': ['नारायणपुर', 'नारायणपूर'], 'Orchha': ['ओरछा']},
    "642": {'Chhindgarh': ['छिंदगढ़', 'छिन्द्गढ़'], 'Dornapal': ['दोरनापाल'], 'Gadiras': ['गाड़ीरास'], 'Jagargunda': ['जगरगुंडा'], 'Konta': ['कोंटा'], 'Sukma': ['सुकमा'], 'Tongpal': ['तोंगपाल']},
    "643": {'Baderajpur': ['बड़ेराजपुर', 'बदेराजपुर'], 'Dhanora': ['धनोरा'], 'Keshkal': ['केशकाल'], 'Kondagaon': ['कोंडागांव', 'कोंड़ागांव'], 'Makdi': ['माकडी'], 'Mardapal': ['मरदापाल'], 'Pharasgaon': ['फरसगांव']},
    "644": {'Balodabazar': ['बलोदाबाज़ार'], 'Bhatapara': ['भाटापारा'], 'Kasdol': ['कसडोल'], 'Lavan': ['लवन'], 'Palari': ['पलारी'], 'Simga': ['सिमगा'], 'Sonakhan': ['सोनाखान'], 'Suhela': ['सुहेला'], 'Tundara': ['टुंडरा']},
    "645": {'Amlipadar': ['अमलीपदर'], 'Chhura': ['छुरा'], 'Devbhog': [], 'Fingeshwar': ['फिंगेश्वर'], 'Gariyaband': ['गरियाबंद'], 'Mainpur': ['मैनपुर'], 'Rajim': ['राजिम']},
    "646": {'Arjunda': ['अर्जुन्दा'], 'Balod': ['बालोद'], 'Daundi': [], 'Daundilohara': ['डौंडीलोहारा'], 'Gunderdehi': ['गुंडरदेही', 'गुन्दरदेही'], 'Gurur': ['गुरुर'], 'Marri Bangla(Deori)': []},
    "647": {'Jarhagaon': ['जरहागाँव', 'जरहागांव'], 'Lalpur Thana': [], 'Lormi': ['लोरमी'], 'Mungeli': ['मुंगली', 'मुंगेली'], 'Pathariya': ['पथरिया'], 'Sargaon': ['सरगांव']},
    "648": {'Bhaiyathan': ['भैयाथान'], 'Bhatgaon': ['भटगाँव', 'भटगांव'], 'Biharpur': ['बिहारपुर'], 'Latori': ['लटोरी'], 'Odgi': ['ओडगी'], 'Pratappur': ['प्रतापपुर'], 'Premnagar': ['प्रेमनगर'], 'Ramanujnagar': ['रामानुजनगर'], 'Surajpur': ['सूरजपुर']},
    "649": {'Balrampur': ['बलरामपुर'], 'Chalgali': [], 'Chando': ['चंदो'], 'Daura-Kochali': [], 'Kusmi(Samri)': ['कुसमी'], 'Raghunathnagar': ['रघुनाथनगर'], 'Rajpur': ['राजपुर'], 'Ramanujganj': ['रामानुजगंज'], 'Ramchandrapur': ['रामचन्द्रपुर'], 'Samri': [], 'Shankargarh': ['शंकरगढ़', 'शंकरगढ़ (बचवर)'], 'Wadrafnagar': ['वाड्रफनगर']},
    "650": {'Bemetara': ['बेमेतरा'], 'Berla': ['बेरला'], 'Bhimbhauri': [], 'Darhi': [], 'Devkar': ['देवकर'], 'Nandghat': ['नन्दघाट'], 'Nawagarh': ['नवागढ़'], 'Saja': ['साजा'], 'Thankhamariya': []},
    "734": {'Marwahi': ['मरवाही'], 'Pendra': ['पेंड्रा'], 'Pendra Road': [], 'Sakola': ['सकोला']},
    "759": {'Chhuikhadan': ['छुईखदान'], 'Gandai': ['गंडई', 'गन्दी'], 'Khairagarh': ['खैरागढ़'], 'Salhewara': ['साल्हेवारा']},
    "760": {'Bharatpur': ['भरतपुर'], 'Chirmiri': ['चिरमिरी'], 'Kelhari': ['केल्हारी'], 'Khadganva': [], 'Kotadol': ['कोटाडोल'], 'Manendragarh': ['मनेन्द्रगढ', 'मनेन्द्रगढ़', 'महेंद्रगढ़']},
    "761": {'Ambagarh Chouki': [], 'Aundhi': ['औंधी'], 'Khadgaon': ['खडगाँव'], 'Manpur': ['मानपुर', 'मानपुर(तद)'], 'Mohla': ['मोहला']},
    "762": {'Adbhar': ['अड़भार', 'अड्भर'], 'Bhothiya': ['भोथिया'], 'Chandrapur': ['चंद्रपुर', 'चन्द्रपुर'], 'Dabhra': ['डभरा'], 'Hasoud': [], 'Jaijaipur': ['जैजैपुर'], 'Malkharoda': ['मालखरोदा'], 'Naya Baradwar': ['नया बाराद्वार'], 'Sakti': ['सकती']},
    "763": {'Baramkela': ['बरमकेला'], 'Bhatgaon': ['भटगांव'], 'Bilaigarh': ['बिलाई गढ़', 'बिलाईगढ़'], 'Sarangarh': ['सारंगगढ़'], 'Sariya': ['सरिया'], 'Sarsiwa': []},
}
# the post words before the place ("न्यायालय अतिरिक्त तह्सीलदार", "अनुविभागीय अधिकारी (रा.)")
POST_WORDS = re.compile(r"(न्यायालय|कार्यालय|अतिरिक्त|अति\.|नायब|प्रभारी|तह?्?सीलदार|तहसील|अनुविभागीय|अधिकारी|दंडाधिकारी|दण्डाधिकारी|"
                        r"\((रा\.?|राजस्व)\s*\)|राजस्व|एवं|वृत्त|नजूल)")
VACANT = re.compile(r"^(रिक्त|vacant|-+|0+)$", re.I)
_V = {"अ": "a", "आ": "a", "इ": "i", "ई": "i", "उ": "u", "ऊ": "u", "ऋ": "ri", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au"}
_M = {"ा": "a", "ि": "i", "ी": "i", "ु": "u", "ू": "u", "ृ": "ri", "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ॉ": "o", "ॅ": "e"}
_C = {"क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n", "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "n", "ट": "t", "ठ": "th",
      "ड": "d", "ढ": "dh", "ण": "n", "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n", "प": "p", "फ": "ph", "ब": "b", "भ": "bh",
      "म": "m", "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh", "ष": "sh", "स": "s", "ह": "h", "ळ": "l"}


def translit(s):
    """A plain Latin spelling of a Devanagari place ("आरंग" -> "Arang", "मंदिर हसौद" -> "Mandir Hasaud"); Latin text is kept.
    The inherent vowel is dropped at the end of a word and between a sounded and a vowel-marked syllable (Hindi schwa deletion)."""
    out = []
    for word in _esw.clean(s).split(" "):
        units, chars, i = [], list(word.replace("\u093c", "")), 0     # units: [consonant or vowel text, vowel, nasal, explicit]
        while i < len(chars):
            c = chars[i]
            nxt = chars[i + 1] if i + 1 < len(chars) else ""
            if c in _C:
                if nxt in _M:
                    units.append([_C[c], _M[nxt], "", True])
                    i += 1
                elif nxt == "\u094d":
                    units.append([_C[c], "", "", True])
                    i += 1
                else:
                    units.append([_C[c], "a", "", False])
            elif c in _V:
                units.append(["", _V[c], "", True])
            elif c in "\u0902\u0901" and units:
                units[-1][2] = "n"
            elif c == "\u0903" and units:
                units[-1][2] = "h"
            elif c not in "\u094d":
                units.append([c, "", "", True])
            i += 1
        for j, u in enumerate(units):
            if u[3] or not u[0] or j == 0:
                continue
            last = j == len(units) - 1
            if (last and not u[2]) or (not last and units[j + 1][3] and units[j + 1][1] and units[j - 1][1]):
                u[1] = ""
        w = "".join(a + b + c for a, b, c, _ in units)
        out.append(w[:1].upper() + w[1:])
    return " ".join(x for x in out if x)


def hkey(s):
    """Hindi spelling key: no anusvara, chandrabindu, nukta or halant; long and short i / u the same."""
    s = re.sub("[ंँ़्‌‍\\s.-]", "", s or "")
    return s.replace("ी", "ि").replace("ू", "ु").replace("ॉ", "ो")


def place_of(text):
    """The place in a post cell: 'न्यायालय तहसीलदार, आरंग' -> 'आरंग'; 'अनुविभागीय अधिकारी (रा.) तिलदा-नेवरा' -> 'तिलदा-नेवरा'."""
    s = POST_WORDS.sub(" ", _esw.clean(text))
    return _esw.clean(re.sub(r"^[\s,.:;()-]+|[\s,.:;()-]+$", "", re.sub(r"\s*,\s*", " ", s)))


def lgd_name(place, dc):
    """LGD sub-district name for a Hindi place in LGD district dc (also tried: each part of 'तिलदा-नेवरा'), else None."""
    names = TAHSILS.get(dc, {})
    tries = [place] + [p for p in re.split(r"\s*[-/]\s*", place) if p and p != place]
    for t in tries:
        k = hkey(t)
        for en, his in names.items():
            if k and any(hkey(h) == k for h in his):
                return en
    for t in tries:
        lat = re.sub(r"[^a-z]", "", translit(t).lower())
        if len(lat) < 3:
            continue
        keys = {re.sub(r"[^a-z]", "", en.lower()): en for en in names}
        got = difflib.get_close_matches(lat, list(keys), n=1, cutoff=0.8)
        if got:
            return keys[got[0]]
    return None


def items(get=None):
    return [{"key": f"sub2_cg_{sid}", "payload": {"reader": MODULE, "url": URL, "district_id": sid, "district": name, "district_code": dc,
                                                  "state": "CG", "india_only": True}}
            for sid, (dc, name) in DISTRICTS.items()]


def hidden(html):
    """The hidden ASP.NET fields of a page (__VIEWSTATE, __EVENTVALIDATION, ...)."""
    out = {}
    for i in _esw.soup(html).find_all("input", type="hidden"):
        if i.get("name"):
            out[i["name"]] = i.get("value", "")
    return out


def designations(html):
    sel = _esw.soup(html).find("select", id="ddlDesignation")
    return [o.get("value") for o in sel.find_all("option") if o.get("value")] if sel else []


def rows(html):
    """[(post cell, name, mobile)] of the result table GridView1."""
    t = _esw.soup(html).find("table", id="GridView1")
    if t is None:
        return []
    out = []
    for r in _esw.grid(t)[1:]:
        if len(r) >= 4:
            out.append((r[1], r[2], r[3]))
    return out


def build(code, found, p, seen):
    post, dept, level = POSTS[code]
    sid, dc, district = str(p["district_id"]), p.get("district_code", ""), p.get("district", "")
    recs = []
    for cell, name, mobile in found:
        name = _esw.clean(name)
        if not name or VACANT.match(name):
            continue
        hi = place_of(cell)
        this = post
        if level == "subdistrict":     # the tahsildar list also holds additional and naib tahsildars' courts
            this = ("Naib Tahsildar" if re.search(r"नायब|नाय\.", cell) else "Additional Tahsildar" if re.search(r"अतिरिक्त|अति\.", cell)
                    else post)
        en = lgd_name(hi, dc) if hi else None
        area = en or translit(hi) or district
        base = f"CG-{sid}-{code}-{_esw.slug(area) or 'x'}"
        key, i = base, 2
        while key in seen:
            key, i = f"{base}:{i}", i + 1
        seen.add(key)
        recs.append(_esw.record(MODULE, key, dept=dept, level=level, area=area, area_regional=hi, post=this, name=name,
                                phone=_esw.phones(mobile), district=district, district_code=dc, state="CG", office=_esw.clean(cell),
                                office_id=f"CG-REV-{sid}-{code}-{_esw.slug(area) or 'x'}", source=URL, lgd_match=bool(en)))
    return recs


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "home", r.content)]
    sid = str(p["district_id"])
    form = hidden(r.text)
    d = get(url, method="POST", data={**form, "__EVENTTARGET": "ddlDistrict", "__EVENTARGUMENT": "", "ddlDistrict": sid,
                                      "ddlDesignation": ""})
    if d is None:
        return [], files, "no answer to the district postback"
    files.append(_esw.keep(MODULE, f"district-{sid}", d.content))
    have = designations(d.text)
    if not have:
        return [], files, "no post list"
    form = hidden(d.text)
    recs, seen = [], set()
    for code in POSTS:
        if code not in have:
            continue
        a = get(url, method="POST", data={**form, "__EVENTTARGET": "ddlDesignation", "__EVENTARGUMENT": "", "ddlDistrict": sid,
                                          "ddlDesignation": code})
        if a is None:
            continue
        files.append(_esw.keep(MODULE, f"district-{sid}-post-{code}", a.content))
        recs += build(code, rows(a.text), p, seen)
    return recs, files, "" if recs else "no rows"
