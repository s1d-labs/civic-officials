"""Nudi (legacy Kannada font) -> Unicode converter (cforms/cn_nudi.py), checked on the Karnataka SEC result abstract of
3 September 2018 (karsec.karnataka.gov.in/FileDoc/PreviousElection/Result/24/ULB Results 2018-Phase-1.pdf, fetched 2026-11-12;
its pdftotext -layout text is saved next to it)."""
from pathlib import Path

from cforms.cn_nudi import convert, is_nudi

D = Path(__file__).parent / "data" / "cn_nudi"


def _lines():
    return [" ".join(l.split()) for l in (D / "karsec_ulb_2018_phase1_layout.txt").read_text(encoding="utf-8").splitlines()]


def test_cn_nudi_title_and_headers():
    out = [convert(l) for l in _lines() if is_nudi(l)]
    assert "ನಗರ ಸ್ಥಳೀಯ ಸಂಸ್ಥೆಗಳ ಸಾರ್ವತ್ರಿಕ ಚುನಾವಣೆ, 2018" in out
    assert "ದಿನಾಂಕ: 03-09-2018 ರಂದು ಮತಗಳ ಎಣಿಕೆಯ ಪಕ್ಷವಾರು ಪಡೆದ ಮತಗಳ ಅಂಕಿ ಅಂಶಗಳು" in out
    assert "ಪಕ್ಷವಾರು ಪಡೆದ ಮತಗಳು (ಇ.ವಿ.ಎಂ. ಮತಗಳು ಮತ್ತು ಅಂಚೆ ಮತಗಳು ಸೇರಿದಂತೆ)" in out
    assert "ಇಂಡಿಯನ್ ನ್ಯೂ ಕಾಂಗ್ರೆಸ್" in out and "ಕ್ರ. ಜಿಲ್ಲೆಯ ನಗರ ಸ್ಥಳೀಯ ಒಟ್ಟು" in out and "ನೋಟಾ" in out


def test_cn_nudi_district_rows():
    names = {l.split()[0]: convert(" ".join(l.split()[1:3])) for l in _lines() if l[:1].isdigit() and is_nudi(l)}
    want = {"1": "ಚಿತ್ರದುರ್ಗ", "2": "ದಾವಣಗೆರೆ", "3": "ಶಿವಮೊಗ್ಗ", "4": "ತುಮಕೂರು", "5": "ಮೈಸೂರು", "7": "ದಕ್ಷಿಣ ಕನ್ನಡ",
            "8": "ಉಡುಪಿ", "10": "ಮಂಡ್ಯ", "11": "ಬೆಳಗಾವಿ", "12": "ವಿಜಯಪುರ", "13": "ಬಾಗಲಕೋಟೆ", "16": "ಉತ್ತರ ಕನ್ನಡ", "18": "ಕೊಪ್ಪಳ",
            "20": "ರಾಯಚೂರು", "21": "ಬೀದರ್", "22": "ಯಾದಗಿರಿ"}
    for k, v in want.items():
        assert names[k].startswith(v), (k, names[k])


def test_cn_nudi_words_and_detection():
    assert convert("PÀ£ÁðlPÀ gÁdå ZÀÄ£ÁªÀuÁ DAiÉÆÃUÀ") == "ಕರ್ನಾಟಕ ರಾಜ್ಯ ಚುನಾವಣಾ ಆಯೋಗ"
    assert convert("¸ÀzÀ¸ÀågÀ ºÉ¸ÀgÀÄ") == "ಸದಸ್ಯರ ಹೆಸರು" and convert("ªÁqÀð ¸ÀASÉå") == "ವಾರ್ಡ ಸಂಖ್ಯೆ"
    assert convert("²ªÀ¸ÃÉ£É") == "ಶಿವಸೇನೆ" and convert("¥ÀPÀëUÀ¼ÄÀ") == "ಪಕ್ಷಗಳು"
    assert is_nudi("£ÀUÀgÀ ¸ÀÜ½ÃAiÀÄ") and not is_nudi("Ward No 12 Ramesh Kumar") and not is_nudi("ನಗರ ಸ್ಥಳೀಯ")
