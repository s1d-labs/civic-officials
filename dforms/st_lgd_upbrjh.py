"""LGD district names and codes of Uttar Pradesh, Bihar and Jharkhand (DB civic lgd.districts, 2026-11-13) with the other
spellings that the state lists use (old names, police district names). district(state, text) finds the district a post text names."""
import re

DISTRICTS = {
    "UP": {"Agra": "118", "Aligarh": "119", "Ambedkar Nagar": "121", "Amethi": "640", "Amroha": "154", "Auraiya": "122", "Ayodhya": "140", "Azamgarh": "123", "Baghpat": "124", "Bahraich": "125", "Ballia": "126", "Balrampur": "127", "Banda": "128", "Bara Banki": "129", "Bareilly": "130", "Basti": "131", "Bhadohi": "179", "Bijnor": "132", "Budaun": "133", "Bulandshahr": "134", "Chandauli": "135", "Chitrakoot": "136", "Deoria": "137", "Etah": "138", "Etawah": "139", "Farrukhabad": "141", "Fatehpur": "142", "Firozabad": "143", "Gautam Buddha Nagar": "144", "Ghaziabad": "145", "Ghazipur": "146", "Gonda": "147", "Gorakhpur": "148", "Hamirpur": "149", "Hapur": "661", "Hardoi": "150", "Hathras": "163", "Jalaun": "151", "Jaunpur": "152", "Jhansi": "153", "Kannauj": "155", "Kanpur Dehat": "156", "Kanpur Nagar": "157", "Kasganj": "633", "Kaushambi": "158", "Kheri": "159", "Kushinagar": "160", "Lalitpur": "161", "Lucknow": "162", "Mahoba": "165", "Mahrajganj": "164", "Mainpuri": "166", "Mathura": "167", "Mau": "168", "Meerut": "169", "Mirzapur": "170", "Moradabad": "171", "Muzaffarnagar": "172", "Pilibhit": "173", "Pratapgarh": "174", "Prayagraj": "120", "Rae Bareli": "175", "Rampur": "176", "Saharanpur": "177", "Sambhal": "659", "Sant Kabir Nagar": "178", "Shahjahanpur": "180", "Shamli": "660", "Shrawasti": "181", "Siddharthnagar": "182", "Sitapur": "183", "Sonbhadra": "184", "Sultanpur": "185", "Unnao": "186", "Varanasi": "187"},
    "BR": {"Araria": "188", "Arwal": "611", "Aurangabad": "189", "Banka": "190", "Begusarai": "191", "Bhagalpur": "192", "Bhojpur": "193", "Buxar": "194", "Darbhanga": "195", "Gaya": "196", "Gopalganj": "197", "Jamui": "198", "Jehanabad": "199", "Kaimur (Bhabua)": "200", "Katihar": "201", "Khagaria": "202", "Kishanganj": "203", "Lakhisarai": "204", "Madhepura": "205", "Madhubani": "206", "Munger": "207", "Muzaffarpur": "208", "Nalanda": "209", "Nawada": "210", "Pashchim Champaran": "211", "Patna": "212", "Purbi Champaran": "213", "Purnia": "214", "Rohtas": "215", "Saharsa": "216", "Samastipur": "217", "Saran": "218", "Sheikhpura": "219", "Sheohar": "220", "Sitamarhi": "221", "Siwan": "222", "Supaul": "223", "Vaishali": "224"},
    "JH": {"Bokaro": "322", "Chatra": "323", "Deoghar": "324", "Dhanbad": "325", "Dumka": "326", "East Singhbum": "327", "Garhwa": "328", "Giridih": "329", "Godda": "330", "Gumla": "331", "Hazaribagh": "332", "Jamtara": "333", "Khunti": "606", "Koderma": "334", "Latehar": "335", "Lohardaga": "336", "Pakur": "337", "Palamu": "338", "Ramgarh": "607", "Ranchi": "339", "Sahebganj": "340", "Saraikela Kharsawan": "341", "Simdega": "342", "West Singhbhum": "343"},
}
ALIASES = {
    "UP": {"Allahabad": "120", "Faizabad": "140", "Barabanki": "129", "Raebareli": "175", "Bagpat": "124", "Noida": "144", "GB Nagar": "144", "Gautam Buddh Nagar": "144", "Lakhimpur Kheri": "159", "Bhadoi": "179", "Sant Ravidas Nagar": "179", "Maharajganj": "164", "Padrona": "160", "Shravasti": "181", "Siddharth Nagar": "182", "Sidharthnagar": "182", "Kabir Nagar": "178", "Ramabai Nagar": "156", "Fatehgarh": "141", "JP Nagar": "154", "Budaun": "133", "Badaun": "133", "Kanpur": "157", "Kanpur Nagar": "157", "Muzaffar Nagar": "172", "Bulandshahar": "134", "Siddharthanagar": "182", "Kushi Nagar": "160", "Sant Ravidas Nagar Bhadohi": "179"},
    "BR": {"West Champaran": "211", "East Champaran": "213", "Bettiah": "211", "Motihari": "213", "Purnea": "214", "Kaimur": "200", "Bhabua": "200", "Bagaha": "211", "Naugachia": "192", "Nawadah": "210", "Chapra": "218", "Hajipur": "224", "Sasaram": "215"},
    "JH": {"East Singhbhum": "327", "Jamshedpur": "327", "Chaibasa": "343", "Seraikela": "341", "Saraikela": "341", "Sahibganj": "340", "Hazaribag": "332", "Daltonganj": "338", "Medininagar": "338"},
}


def key(s):
    return re.sub(r"[^a-z]", "", (s or "").lower())


_IDX = {}


def index(state):
    if state not in _IDX:
        names = {key(n): (c, n) for n, c in DISTRICTS.get(state, {}).items()}
        lgd = {c: n for n, c in DISTRICTS.get(state, {}).items()}
        for n, c in ALIASES.get(state, {}).items():
            names.setdefault(key(n), (c, lgd[c]))
        _IDX[state] = sorted(names.items(), key=lambda x: -len(x[0]))
    return _IDX[state]


def district(state, text):
    """(LGD code, LGD name) of the first district named in text (longest name first, letters only), else ("", "")."""
    words = re.sub(r"[^a-z]+", " ", (text or "").lower()).split()
    flat = [w for w in words]
    for k, v in index(state):
        # a district name must stand as whole words: join 1-3 neighbouring words and compare
        for i in range(len(flat)):
            for j in range(i + 1, min(i + 4, len(flat) + 1)):
                if "".join(flat[i:j]) == k:
                    return v
    return "", ""
