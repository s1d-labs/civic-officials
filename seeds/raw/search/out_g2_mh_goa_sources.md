# Multi-body sources: Maharashtra and Goa (checked 2026-11-09/10 from vpsin, India)

## 1. District NIC "public utilities: municipality" pages (S3WaaS)
Each page has one card per body: name, address, often the chief officer's email and phone. Some cards also give a website link.
The pages show 10 cards each; continue at `/page/2/`.
- Pages that loaded (200): ahilyanagar.maharashtra.gov.in, akola.gov.in (also /corporation/), amravati.gov.in, beed.gov.in, bhandara.gov.in,
  buldhana.nic.in, chanda.nic.in, chhatrapatisambhajinagar.maharashtra.gov.in, dharashiv.maharashtra.gov.in, dhule.gov.in, gadchiroli.gov.in,
  gondia.gov.in, jalgaon.gov.in, jalna.gov.in, kolhapur.gov.in (/municipal-corporation-municipalities/), latur.gov.in, mumbaisuburban.gov.in
  (/municipal-corporation/), nanded.gov.in, nandurbar.gov.in, northgoa.gov.in, palghar.gov.in, parbhani.gov.in, pune.gov.in (corporations only),
  raigad.gov.in (also /municipal-corporation/), ratnagiri.gov.in, sangli.nic.in (/municipalty/), solapur.gov.in, thane.nic.in, wardha.gov.in,
  washim.gov.in, yavatmal.gov.in. Path: `/en/public-utility-category/municipality/`. Some sites omit `/en/`.
- Pages that did not load: satara.gov.in (timeout), sindhudurg.gov.in, hingoli.gov.in, southgoa.gov.in (503). nagpur.gov.in has no such page (404).
- Note: many districts moved to `<district>.maharashtra.gov.in`; old nic.in and gov.in names redirect.

## 2. District pages with a table or list
- https://ahilyanagar.maharashtra.gov.in/en/municipal-administration/ : all 16 bodies, commissioner or chief officer NAME, phone, email.
- https://nashik.gov.in/en/municipal-council/ : 9 councils, phone and email.
- https://thane.nic.in/municipal-corporations/ : 6 corporations with website links. https://thane.nic.in/en/municipal-councils/ : 2 councils with websites.
- https://parbhani.gov.in/en/municipal-council-administration/ : quick links to 8 council sites (`<name>mahaulb.maharashtra.gov.in`).
- https://pune.gov.in/en/nagarpalika-branch/ : Pune councils (class, year, area, population). No contacts.

## 3. State host for council websites: `<slug>mahaulb.maharashtra.gov.in`
District pages (Bhandara, Jalna, Solapur, Chh. Sambhajinagar, Parbhani, Thane) link council sites on this pattern.
All names resolve to one IP (115.124.114.116). There is no DNS wildcard, so a name that resolves is an existing site.
I resolved name variants for every Maharashtra body: 331 bodies in the output use such a site name. The host timed out from India and from Germany
on 2026-11-09 and 2026-11-10. So these websites are NOT verified. Same-name bodies (Karanja, Malegaon, Malkapur, Shirur, Vadgaon) share
one plain slug: the assignment is marked "probable". Karjat (two bodies) is left blank.

## 4. Other
- https://mahaulb.in/MahaULB/home/ulblist/viewmore : MahaULB ULB list. It returned HTTP 500 twice. Retry later; it can list all ULBs.
- Goa: https://goaulbservice.gov.in/ is the state ULB portal. Curchorem.aspx, Margao.aspx and Mormugao.aspx open directly.
  The other councils open only by a form button (postback). Per council: ElectedMembers.aspx (councillors) and AbtStaff.aspx (staff),
  in the council session. Margao has its own site https://mmcmargao.goa.gov.in/ (/councillors/, /about-us/who-is-who/).
  Panaji: https://ccpgoa.com/elected-members/.
- Goa SEC publishes winning-candidate PDFs per council (sec.goa.gov.in/wp-content/uploads/2023/05/winning-candidates-<council>.pdf), seen in search, not fetched.

Raw pages: /tmp/claude-1002/search/mh_nic/p, /tmp/claude-1002/search/mh_nic/pg, parsed cards /tmp/claude-1002/search/mh_nic/cards.json, DNS hits /tmp/claude-1002/search/mh_nic/dns_hits.txt.
