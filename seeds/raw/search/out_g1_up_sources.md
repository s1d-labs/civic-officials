# Uttar Pradesh urban local bodies: multi-body sources (g1_up)

Checked 2026-11-09/10. "From India" = fetched through vpsin (87.76.191.50).

## Sources that list many bodies

| URL | What it covers | Status |
|---|---|---|
| http://localbodies.up.nic.in/listnn.htm | All 17 nagar nigams: website, mayor + mobile, commissioner + phone + email | Loads (saved copy in /tmp/claude-1002/ulb-platforms/uttarpradesh-listnn.html). Used for all 17 NN rows. |
| http://localbodies.up.nic.in/pdf/elected-npp.pdf | Chairperson (adhyaksh) + mobile for every nagar palika parishad (2023 election) | Loads. Used as the fallback officials_url for NPPs. |
| http://localbodies.up.nic.in/pdf/elected-np.pdf | Chairperson + mobile for every nagar panchayat | Used as the fallback officials_url for NPs. |
| https://e-nagarsewaup.gov.in/ulbappsmain/showUlbList?type=NN / NPP / NP | State ULB list pages linked from localbodies.up.nic.in/ulbdetails.html; may carry per-ULB links | Timed out from India and from Germany (2026-11-09). Not in the Wayback Machine. Retry later. |
| https://<district>.nic.in/public-utility-category/municipality/ (S3WaaS district sites) | Per district: each NPP/NP with address, email, phone, often "Website Link". 63 of 75 district sites have such a category page or a NPP/NP list page. Examples: etawah.nic.in (6 bodies with email, phone, site), rampur.nic.in (npprampur.gov.in), mainpuri.nic.in, jaunpur.nic.in, ghaziabad.nic.in, mirzapur.nic.in | Loads from Germany. Crawl result: /tmp/claude-1002/search/up_raw/dall.json |
| https://<district>.nic.in/public-utility/<nagar-palika-parishad-x>/ and bijnor.nic.in/nagar-palika-parishad-<x>/ | One page per body on some district sites (Bijnor, Etah, Etawah, Jaunpur, Deoria, Ballia, Saharanpur, Barabanki ...) with phone, email, website | Used as officials_url when the body has no own officials page. |
| https://kmc.up.nic.in/english/key-contacts.html | Kanpur NN officers: name, designation, mobile, email | Timed out from India in the test. |

## Sources checked with no useful result
- igod.gov.in (local copy in the India Gov Status DB): only the nagar nigams (Agra, Aligarh, Jhansi, Kanpur, Lucknow, Gorakhpur, Moradabad, Ghaziabad). No NPP/NP.
- india.gov.in "website-<district>-district-uttar-pradesh" pages: these are district website directories. Not crawled (about 15-20 pages per district).
- Web search, body by body: low yield (about 1 in 4 queries gives a body site).

## Method that gave most body sites
Guessing vendor domains (npp<town>.com/.in/.org/.co.in, np<town>.*, nagarpanchayat<town>.*, <town>npp.in, <town>np.*), DNS lookup of about 38,000 names, then a page check (the page must name a nagar palika/panchayat and Uttar Pradesh or the district). Parked, casino and for-sale domains were rejected. Same-name towns were resolved by the district on the page.

## Result (out_g1_up.csv, 770 rows)
- Websites: NN 17/17 (15 load from India), NPP 71/200 (58 load), NP 73/545 (66 load), NAC 4/8 (1 loads).
- officials_url: own site page for 118 bodies, district NIC page with body phone/email for 135, state chair lists (elected-npp.pdf / elected-np.pdf / listnn.htm) for 510; 7 NACs have none.
- Rejected same-name candidates are named in the notes column (Lal Gopal Ganj, Aurangabad, Ramnagar, Rampura, Wazirganj).
- Work files: /tmp/claude-1002/search/up_raw/ (dall.json district crawl, classify.txt domain checks, india/*.raw pages fetched from India), scripts in /tmp/claude-1002/search/up_scripts/.
