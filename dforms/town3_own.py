"""Town bodies' own websites of single vendors (no shared template): the office staff from the site's staff, employee or
officer page. One reader for all of them: the page has a staff table (a name column and a designation column) in English,
Hindi or Gujarati, read by dforms/_town3.staff_rows.

Sites (dforms/town3_sites.json, reader town3_own; found as dforms/_town3.py says, 2026-11-13), with the page and its table:
- Odisha: Choudwar (Directory.html), Gunupur and Joda (employee.php, with Date of Joining), Paradeep (Section.html), Phulabani
  (staffs.php: Name | Designation & Contact), Tarbha (Staff.html).
- Uttar Pradesh: Anpara (employee: नाम | संपर्क सूत्र | पद), Kundarki (Staff_Members.aspx: अधिकारी/कर्मचारी का नाम | पद का नाम |
  पिता / पति | मोबाइल | ई.मेल), Kunwargaon and Nizamabad (officer.html + employee.html), Mataundh (WebController/Officer),
  Mubarakpur (employee), Zaidpur (Home/ContactUs).
- Haryana: Palwal (employee_data), Radaur (webhome/office-directory), Rewari (officers-directory, Drupal).
- Himachal Pradesh: Rampur and Theog (Web/officer, Web/Employee), Nirmand (Home/official).
- Punjab: Zirakpur (OrganizationList.aspx). Madhya Pradesh: Katangi (staff.html, शाखा का नाम | कर्मचारी का नाम | पदनाम).
- Gujarat: Keshod (content.aspx?Id=473: કર્મચારીનું નામ | હોદ્દો | શાખા), Dholka (Nagarpalika/staff.html: કર્મચારીનું પુરૂ નામ |
  હોદ્દો | સરનામું | મોબાઈલ નંબર; the Chief Officer is written ચીફ ઓફીસર), Himatnagar (Staffs.html, by department).
- Uttar Pradesh also: Ghatampur (employe.html: कर्मचारी नाम | पिता का नाम | पद नाम | Departmental Work | मोबाइल नम्बर).
Left out on purpose: Islamnagar (its page lists the staff of Kundarki), Daranagar and Renukoot (the rows of Anpara), Petlad
(a list of past chief officers), Roun (placeholder rows), and sites whose host name fits a town of another state.
Samples (live from India, dev-vps-3 Mumbai, 2026-11-13). Route "direct" (not checked from abroad), india_only.
Records: dept town_body, level body, area = LGD body name, lgd_code; ids dept:town3_own:<site>:<post slug>:<name slug>.
"""
from dforms import _town3

METHOD = "html table"

MODULE = "town3_own"
SITES = _town3.sites(MODULE)


def items(get=None):
    return _town3.items(MODULE, SITES)


def fetch(p, get):
    return _town3.fetch(MODULE, p, get)
