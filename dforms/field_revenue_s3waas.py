"""All states: revenue field staff per village, halqa or circle (patwari / halqa patwari, VAO, village accountant, revenue
inspector / firka RI, kanungo / girdawar) and the tehsil / taluk / mandal / circle offices above them (tehsildar, mamlatdar,
naib tehsildar, circle officer), from district portals (S3WaaS):
- HTML pages: "Know your Patwari" (Shopian 50 patwaris with mobiles, Anantnag), "VAO Contact Directory" (Perambalur: 152
  villages with the VAO's mobile, no names), "RI contact details" (Perambalur), "Tehsil" pages (UP, MP, GJ, TS, JK).
- PDF lists linked from those pages (payload "page" = the page that links them; cdn.s3waas.gov.in files are not in the
  archive, so the hub fetches them): Gurdaspur "Patwari name, kanungo circle, patwar circle and mobile number" (one PDF per
  tehsil, 2022), Hoshiarpur "Know Your Patwari" (one PDF per tehsil / sub tehsil, 2018: kanungo, patwar circle, patwari,
  villages of the circle, mobiles), Thoothukudi "VAO and firka RI phone numbers" (2026: 522 villages, 184 with a mobile; 42
  firka RIs), Poonch "Revenue hierarchy" (2025: DC to girdawar and patwari).
- Scanned PDFs (payload "needs_ocr": true; Pathankot, Ludhiana): no text layer. The reader keeps the file in the bucket and
  returns "no table ... needs OCR"; an OCR task can read the stored copy later.
Read by dforms/_field.py (layer "revenue", level per row: section = patwari halqa / VAO village, circle = RI / kanungo
circle, subdistrict = tehsil, district). Hoshiarpur gives one row per village of a patwar circle (sub_area = village).
Seed: seeds/dept_field_revenue_s3waas.json. Records: dept revenue, layer field, field_layer revenue.
Ids dept:field_revenue_s3waas:<host>:<page or tag>:<serial or row>.
"""
from dforms import _field

METHOD = "pdf text (pdftotext -layout, else pypdf layout) + json api + html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "field_revenue_s3waas"
items, fetch = _field.reader(MODULE, "revenue")
