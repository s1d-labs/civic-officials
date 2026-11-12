"""Seeds for cforms/ka_sec.py (seeds/councillors_ka_sec.json): the Karnataka State Election Commission press notes that name the
urban local bodies of each election round since 2021, so a town page can say which council is in office and since when.

The SEC (karsec.karnataka.gov.in) publishes NO ward-wise winner names: its "Results" / "Elected" pages (/GV/GetResult, cat
MunicipalCorporation | CityMunicipal | TalukMunicipal | PattanaPanchayat | Elected) and the press notes (/PressRelease/GetList,
85 notes 2015-2025) give party-wise totals per body only, and every file since 2019 is a scan without a text layer. What they do
give is the list of bodies per round. The rows below were read by eye from the rendered pages (2026-11-13) and matched to LGD
local body codes by name and district (civic.ulb); "sha256" is the file the rows were read from: the reader refuses another file.
Rounds before 2021 (August/October 2018, May/November 2019, February 2020) are not listed: those councils' five-year terms ran
from their first meetings (about November 2020 for most) and ended by November 2025 (indicator, not checked per body).
Run: python seeds/build_ka_sec.py (writes seeds/councillors_ka_sec.json)."""
import json
from pathlib import Path

B = "https://karsec.karnataka.gov.in"
CMC, TMC, TP, CC = "City Municipal Council", "Town Municipal Council", "Town Panchayat", "City Corporation"

# (page, data row in that page's table, body (LGD name), body as printed (Kannada), type, district, LGD code, wards in the file)
DEC21 = [(5, 1, "Hebbugodi", "ಹೆಬ್ಬಗೋಡಿ", CMC, "Bengaluru Urban", "276463"), (5, 2, "Jigani", "ಜಿಗಣಿ", TMC, "Bengaluru Urban", "276464"),
         (5, 3, "Chandapura", "ಚಂದಾಪುರ", TMC, "Bengaluru Urban", "276533"), (5, 4, "Bidadi", "ಬಿಡದಿ", TMC, "Bengaluru South", "276526"),
         (5, 5, "Nayakanahatti", "ನಾಯಕನ ಹಟ್ಟಿ", TP, "Chitradurga", "276542"), (5, 6, "Malebennuru", "ಮಲೆಬೆನ್ನೂರು", TMC, "Davanagere", "276556"),
         (5, 7, "Sira", "ಶಿರಾ", CMC, "Tumakuru", "251969"), (5, 8, "Vitla", "ವಿಟ್ಲ", TP, "Dakshina Kannada", "276554"),
         (5, 9, "Kotekar", "ಕೋಟೆಕಾರು", TP, "Dakshina Kannada", "276555"), (5, 10, "Chikkamagaluru", "ಚಿಕ್ಕಮಗಳೂರು", CMC, "Chikkamagaluru", "251965"),
         (5, 11, "Kapu", "ಕಾಪು", TMC, "Udupi", "301055"), (5, 12, "Athni", "ಅಥಣಿ", TMC, "Belagavi", "251812"),
         (5, 13, "Harogeri", "ಹಾರೋಗೇರಿ", TMC, "Belagavi", "276569"), (5, 14, "Mugalakoda", "ಮುಗಳಖೋಡ", TMC, "Belagavi", "276563"),
         (5, 15, "Munavalli", "ಮುನವಳ್ಳಿ", TMC, "Belagavi", "276564"), (5, 16, "Ugar Khurda", "ಉಗಾರಖುರ್ದ", TMC, "Belagavi", "276565"),
         (5, 17, "Mkhubballi", "ಎಂ.ಕೆ. ಹುಬ್ಬಳ್ಳಿ", TP, "Belagavi", "299417"), (5, 18, "Kankanavadi", "ಕಂಕನವಾಡಿ", TP, "Belagavi", "276567"),
         (5, 19, "Naganur", "ನಾಗನೂರ", TP, "Belagavi", "301061"), (5, 20, "Examba", "ಯಕ್ಸಾಂಬ", TP, "Belagavi", "276575"),
         (5, 21, "Chennammana Kittur", "ಚೆನ್ನಮ್ಮನ ಕಿತ್ತೂರು", TP, "Belagavi", "276578"), (5, 22, "Arabhavi", "ಅರಭಾವಿ", TP, "Belagavi", "276577"),
         (5, 23, "Ainapur", "ಐನಾಪುರ", TP, "Belagavi", "276618"), (5, 24, "Shedbala", "ಶೇಡಬಾಳ", TP, "Belagavi", "276579"),
         (5, 25, "Chinchali", "ಚಿಂಚಿಲಿ", TP, "Belagavi", "276477"), (5, 26, "Boragaon", "ಬೋರಗಾಂವ", TP, "Belagavi", "276583"),
         (5, 27, "Kallolli", "ಕಲ್ಲೋಳಿ", TP, "Belagavi", "276576"), (5, 28, "Nalatavada", "ನಲತವಾಡ", TP, "Vijayapura", "276544"),
         (5, 29, "Nidagundi", "ನಿಡಗುಂದಿ", TP, "Vijayapura", "276557"), (5, 30, "Devarahipparagi", "ದೇವರಹಿಪ್ಪರಗಿ", TP, "Vijayapura", "276558"),
         (5, 31, "Alamela", "ಅಲಮೇಲ", TP, "Vijayapura", "276540"), (5, 32, "Managuli", "ಮನಗೂಳಿ", TP, "Vijayapura", "276541"),
         (5, 33, "Kolhara", "ಕೋಲ್ಹಾರ", TP, "Vijayapura", "276543"), (5, 34, "Kamatagi", "ಕಮತಗಿ", TP, "Bagalkote", "301079"),
         (5, 35, "Belagali", "ಬೆಳಗಲಿ", TP, "Bagalkote", "276529"), (5, 36, "Aminagad", "ಅಮೀನಗಡ", TP, "Bagalkote", "276597"),
         (6, 1, "Annigeri", "ಅಣ್ಣಿಗೇರಿ", TMC, "Dharwad", "251896"), (6, 2, "Gadag-Betigeri", "ಗದಗ-ಬೆಟಗೇರಿ", CMC, "Gadag", "251888"),
         (6, 3, "Bankapura", "ಬಂಕಾಪೂರ", TMC, "Haveri", "251913"), (6, 4, "Guttal", "ಗುತ್ತಲ", TP, "Haveri", "276521"),
         (6, 5, "Jali", "ಜಾಲಿ", TP, "Uttara Kannada", None), (6, 6, "Karatagi", "ಕಾರಟಗಿ", TMC, "Koppal", "276496"),
         (6, 7, "Tavaragera", "ತಾವರಗೇರ", TP, "Koppal", "276601"), (6, 8, "Kukanooru", "ಕುಕನೂರ", TP, "Koppal", "276497"),
         (6, 9, "Bhagyanagara", "ಭಾಗ್ಯನಗರ", TP, "Koppal", "276604"), (6, 10, "Kanakgiri", "ಕನಕಗಿರಿ", TP, "Koppal", "276599"),
         (6, 11, "Kurekuppa", "ಕುರೆಕುಪ್ಪ", TMC, "Ballari", "276538"), (6, 12, "Kurugodu", "ಕುರುಗೋಡು", TMC, "Ballari", "276532"),
         (6, 13, "Hosapete", "ಹೊಸಪೇಟೆ", CMC, "Vijayanagara", "251922"), (6, 14, "Hagaribommanahalli", "ಹಗರಿಬೊಮ್ಮನಹಳ್ಳಿ", TMC, "Vijayanagara", "276535"),
         (6, 15, "Mariyammanahalli", "ಮರಿಯಮ್ಮನಹಳ್ಳಿ", TP, "Vijayanagara", "276474"), (6, 16, "Maski", "ಮಸ್ಕಿ", TMC, "Raichur", "276519"),
         (6, 17, "Kavital", "ಕವಿತಾಳ", TP, "Raichur", "276522"), (6, 18, "Turvihal", "ತುರ್ವಿಹಾಳ", TP, "Raichur", "276524"),
         (6, 19, "Balaganur", "ಬಳಗಾನೂರು", TP, "Raichur", "276523"), (6, 20, "Siravara", "ಸಿರಿವಾರ", TP, "Raichur", "276605"),
         (6, 21, "Kembhavi", "ಕೆಂಭಾವಿ", TMC, "Yadgir", "276516"), (6, 22, "Kakkera", "ಕಕ್ಕೇರಾ", TMC, "Yadgir", "276560")]
DEC21 = [r + (None,) for r in DEC21]       # this note gives poll percentages, not ward counts
APR21 = [(1, 1, "Ballari", "ಬಳ್ಳಾರಿ ಮಹಾನಗರ ಪಾಲಿಕೆ", CC, "Ballari", "251927", 39),
         (1, 2, "Vijayapura", "ವಿಜಯಪುರ ಪುರಸಭೆ", TMC, "Bengaluru Rural", "251842", 23),
         (1, 3, "Ramanagara", "ರಾಮನಗರ ನಗರಸಭೆ", CMC, "Bengaluru South", "253186", 31),
         (1, 4, "Channapatna", "ಚನ್ನಪಟ್ಟಣ ನಗರಸಭೆ", CMC, "Bengaluru South", "253185", 31),
         (1, 5, "Gudibanda", "ಗುಡಿಬಂಡೆ ಪಟ್ಟಣ ಪಂಚಾಯತಿ", TP, "Chikkaballapura", "251980", 11),
         (1, 6, "Bhadravati", "ಭದ್ರಾವತಿ ನಗರಸಭೆ", CMC, "Shivamogga", "251952", 35),
         (1, 7, "Tirthahalli", "ತೀರ್ಥಹಳ್ಳಿ ಪಟ್ಟಣ ಪಂಚಾಯತಿ", TP, "Shivamogga", "251950", 15),
         (1, 8, "Belur", "ಬೇಲೂರು ಪುರಸಭೆ", TMC, "Hassan", "252009", 23),
         (1, 9, "Madikeri", "ಮಡಿಕೇರಿ ನಗರಸಭೆ", CMC, "Kodagu", "252037", 23),
         (1, 10, "Bidar", "ಬೀದರ್ ನಗರಸಭೆ", CC, "Bidar", "251867", 35)]
SEP21 = [(2, 1, "Belagavi", "ಬೆಳಗಾವಿ ಮಹಾನಗರ ಪಾಲಿಕೆ", CC, "Belagavi", "251824", 58),
         (2, 2, "Hubballi-Dharwad", "ಹುಬ್ಬಳ್ಳಿ-ಧಾರವಾಡ ಮಹಾನಗರ ಪಾಲಿಕೆ", CC, "Dharwad", "251893", 82),
         (2, 3, "Kalaburagi City Corporation", "ಕಲಬುರಗಿ ಮಹಾನಗರ ಪಾಲಿಕೆ", CC, "Kalaburagi", "248127", 55),
         (3, 1, "Dod Ballapur", "ದೊಡ್ಡಬಳ್ಳಾಪುರ", CMC, "Bengaluru Rural", "251992", 31),
         (3, 2, "Tarikere", "ತರೀಕೆರೆ", TMC, "Chikkamagaluru", "251962", 23)]
OCT22 = [(2, 1, "Vijayapura", "ವಿಜಯಪುರ ಮಹಾನಗರ ಪಾಲಿಕೆ", CC, "Vijayapura", "251993", 35)]
AUG25 = [(2, 1, "Vemgal-Kurugol", "ವೇಮಗಲ್ ಕುರುಗಲ್", TP, "Kolar", "301054", 17), (2, 2, "Ajjampura", "ಅಜ್ಜಂಪುರ", TP, "Chikkamagaluru", "296977", 11),
         (2, 3, "Kadaba", "ಕಡಬ", TP, "Dakshina Kannada", "296954", 13), (2, 4, "Rattihalli", "ರಟ್ಟಿಹಳ್ಳಿ", TP, "Haveri", "296955", 15),
         (2, 5, "Kalagi", "ಕಾಳಗಿ", TP, "Kalaburagi", "296978", 11)]
DEC25 = [(2, 1, "Bashettihalli", "ಬಾಶೆಟ್ಟಿಹಳ್ಳಿ", TP, "Bengaluru Rural", "299169", 19), (2, 2, "Bajape", "ಬಜಪೆ", TP, "Dakshina Kannada", "299320", 19),
         (2, 3, "Kinnigoli", "ಕಿನ್ನಿಗೋಳಿ", TP, "Dakshina Kannada", "299321", 18), (2, 4, "Manki", "ಮಂಕಿ", TP, "Uttara Kannada", "299328", 20)]

ROUNDS = [
    {"round": "2021-04", "election": "ULB general election, April 2021", "poll_date": "2021-04-27", "result_date": None,
     "url": B + "/FileDoc/PressRelease/All/67/press%20note.pdf", "doc": "SEC press note No. RaChuA 41 IyuBi 2021 of 26-04-2021 (scan)",
     "sha256": "056ee727c68a261ca2d3f21fa2bd806f13187b42f668ff17c05a848ce446b33e", "pages": 2, "rows": APR21},
    {"round": "2021-09", "election": "ULB general election, September 2021", "poll_date": None, "result_date": "2021-09-06",
     "url": B + "/FileDoc/PressRelease/All/70/20210906153501993.pdf", "doc": "SEC press note of 06-09-2021, Form 14 (scan)",
     "sha256": "ac2c360d06f80cffb8374ea70ddeab5ce723ae767e848a6c236e3bf068055c7d", "pages": 3, "rows": SEP21},
    {"round": "2021-12", "election": "ULB general election, December 2021 (58 bodies)", "poll_date": "2021-12-27", "result_date": "2021-12-30",
     "url": B + "/FileDoc/PressRelease/All/71/Rural%20%26%20Urban%20Local%20Bodies%20Elections%20-%20Press%20Note.",
     "doc": "SEC press note No. RaChuA 139 IyuBi 2021 of 27-12-2021, Form 10 (scan)",
     "sha256": "5977870fff47dcf128c4f62cb9c118dc2e1ae4c38584d9af7d32d975722278cf", "pages": 6, "rows": DEC21},
    {"round": "2022-10", "election": "Vijayapura City Corporation general election, October 2022", "poll_date": None, "result_date": "2022-10-31",
     "url": B + "/FileDoc/PressRelease/All/74/ulb%26gp%20results%20oct%202022.pdf", "doc": "SEC press note No. RaChuA 41 IGP 2022 of 31-10-2022 (scan)",
     "sha256": "5ebcd016c744ed565b0e8e8d7d93213f7da3677589ebf08d7796dc79348b5b4e", "pages": 5, "rows": OCT22},
    {"round": "2025-08", "election": "ULB general election of new town panchayats, August 2025", "poll_date": "2025-08-17", "result_date": "2025-08-20",
     "url": B + "/Document/Files/%E0%B2%AA%E0%B2%A4%E0%B3%8D%E0%B2%B0%E0%B2%BF%E0%B2%95%E0%B2%BE%20%E0%B2%AA%E0%B3%8D%E0%B2%B0%E0%B2%95%E0%B2%9F%E0%B2%A3%E0%B3%86%20-%E0%B2%A6%E0%B2%BF%E0%B2%A8%E0%B2%BE%E0%B2%82%E0%B2%95%2020-8-2025%20%E0%B2%B0%20%E0%B2%AB%E0%B2%B2%E0%B2%BF%E0%B2%A4%E0%B2%BE%E0%B2%82%E0%B2%B6",
     "doc": "SEC press note No. SECK/ULB/GELN/1/2025-ULB of 20-08-2025, annex 1 (scan)",
     "sha256": "91cb96020752a970e5e694313efe1804e5ba08a06928cfc8f3dc85ebd6eb2375", "pages": 2, "rows": AUG25},
    {"round": "2025-12", "election": "ULB general election of new town panchayats, December 2025", "poll_date": None, "result_date": "2025-12-24",
     "url": B + "/Document/Files/ULB%20Result%20Press%20Note", "doc": "SEC press note No. SECK/ULB/GELN/2/2025-ULB of 24-12-2025, annex 1 (scan)",
     "sha256": "44d93abbbc011aece5da071bda92642902e49f644092048038855d61580d8158", "pages": 2, "rows": DEC25},
]


def items():
    out = []
    for r in ROUNDS:
        rows = [{"page": pg, "row": n, "body": b, "body_kn": kn, "body_type": t, "district": d, "lgd_code": lgd, "wards": w}
                for pg, n, b, kn, t, d, lgd, w in r["rows"]]
        out.append({"key": f"ka-sec-{r['round']}", "payload": {"kind": "form-ka_sec", "state": "KA", **{k: v for k, v in r.items() if k != "rows"},
                                                              "rows": rows}})
    return out


if __name__ == "__main__":
    p = Path(__file__).with_name("councillors_ka_sec.json")
    p.write_text(json.dumps(items(), ensure_ascii=False, indent=1) + "\n")
    print(p, sum(len(i["payload"]["rows"]) for i in items()), "bodies")
