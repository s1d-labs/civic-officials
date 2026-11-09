# Multi-body sources: Gujarat, Rajasthan, Haryana, Punjab, Himachal Pradesh, Chandigarh (g3, 2026-11-09)

## Rajasthan
- https://lsg.rajasthan.gov.in/<vdir>/ : one Angular site per body. Data comes from /webapi/ by deptCode. List of 260 vdirs: /tmp/claude-1002/ulb-platforms/rajasthan-ulb-sites.tsv. 230 LGD bodies mapped by name (aliases for spelling).
- The shell page answers HTTP 200 for any vdir, also for a vdir that does not exist. A 200 does not prove that the body has a site.
- Extra vdirs with no LGD row: mcjn (Jodhpur North), mckotanorth (Kota North), jaipur Greater is not in the list, UITs, bda, kda, rudsico, ruidp.

## Punjab
- https://lgpunjab.gov.in/cms/ulb-websites.php : 158 links (mostly https://lgpunjab.gov.in/eSewa/<town>/). lgpunjab.gov.in returned 500 / no answer on 2026-11-09.
- State MC-House sites https://mc<name>.punjab.gov.in/Home (councillor pages /Councilors/CouncillorsDetail?mcid=..): live for Amritsar, Ludhiana, Patiala, Bathinda, Moga, Mohali, Hoshiarpur, Phagwara, Pathankot, Batala, Abohar, Barnala, Fatehgarh Churian, Nangal.

## Haryana
- https://ulbharyana.gov.in/Home/StateMunicipalities : 87 bodies (district, type, population), "Website of ULBs" menu with 20 own sites.
- https://ulbharyana.gov.in/Home/PIOList (saved haryana-piolist.html): PIO designation per body, no phones.
- Own sites share one vendor CMS: /contact-us, /elected-members, /officers-directory (or /directory/office-directory). Old per-body pages ulbharyana.gov.in/<id> now show the state home page.

## Gujarat
- https://udd.gujarat.gov.in/corporations.php : 17 corporations, commissioner name + email, mayor/commissioner phones for the old 8. Website links for Mehsana, Morbi, Gandhidham, Porbandar on that page are wrong (copied).
- https://udd.gujarat.gov.in/Nagarpalikas.php : names by class, no links.
- https://collectorjamnagar.gujarat.gov.in/municipality-detail : Jamnagar MC officers with mobile + email. The same path does not exist on other collector sites.
- https://ahmedabad.nic.in/village-panchayats/ : chief officer name, phone, email for Ahmedabad district nagarpalikas.
- Vendor nagarpalika sites (<town>nagarpalika.org/.com): ChiefOfficer.aspx, President.aspx, Contact.aspx.

## Himachal Pradesh
- ud.hp.gov.in did not answer from India on 2026-11-09.
- Common CMS on mc<town>.in / np<town>.in (/Web/Contact, /Web/Officer, links to mcslogin.hp.gov.in "HPMS House Controller"). Many old domains of this pattern are lapsed and now host gambling pages (Nahan, Chamba, Una, Nalagarh, Dehra, Nagrota Bagwan, Banjar, Jogindernagar, Mehatpur, Rajgarh, Chowari).
- https://sechimachal.hp.gov.in/assets/files/ListofMunicipalitiesinHP.pdf : list of municipalities (no contacts).

## Chandigarh
- https://mcchandigarh.gov.in/Directory.aspx : directory.
