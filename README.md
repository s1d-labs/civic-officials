# civic-officials

This family collects the officials that Indian government sites list on their Who's Who, directory and contact pages.

## What it scrapes

- 652 district administration sites, 435 urban local body sites and 250 police unit sites.
- The site list is `sites.csv`. It comes from the India Gov Status list of igod.gov.in sites.
- One project for each kind of site. One queue item for each site.

## How it works

1. The task `whoswho` reads the home page of a site.
2. It finds the links to Who's Who, directory and contact pages. It also tries the usual S3WaaS addresses.
3. It reads each page and stores each table row as a record.
4. On S3WaaS sites, it gets the remaining rows of each list with the site's own "next page" call.
5. It saves each page that it reads to the bucket, under `pages/<site>/`.

## Records

- `type: "row"`: one official or one contact line. Fields: `site`, `kind`, `state`, `page`, `category`, `name`, `designation`,
  `email`, `phone`, `address`, and `cells` (all columns as the site shows them).
- `type: "page"`: one page that the task read, with its title, row count and bucket file.

## Run and test

- Run one site without the hub: `python whoswho.py --local https://patna.nic.in/`
- Run the tests: `python -m pytest tests`
- Run the check against a local hub: `scrape-check --items 2 --project civic-officials-districts`

## Sites that do not answer from abroad

1. Put their domains in `retry_in.txt`, one on each line.
2. Run the Setup workflow.
3. The `civic-officials-in` project then reads them through the hub's Indian proxies.

## OpenStreetMap points and boundaries (task `osm`)

- The project `civic-officials-osm` has one queue item: the Geofabrik India extract (`india-latest.osm.pbf`, about 1.6 GB).
- The task downloads the file once and checks it against the Geofabrik `.md5` file.
- It keeps public-service points (police, fire stations, post offices, schools, colleges, hospitals, clinics, doctors,
  pharmacies, banks, ATMs, courts, town halls, community centres, libraries, social facilities, government offices,
  `healthcare=*`) and admin boundaries (levels 2 to 10, as polygons).
- It saves `osm/<date>/<kind>.geojsonl.gz`, `filtered.osm.pbf`, `manifest.json` and `osm/latest.json` to the family bucket.
- Each feature keeps all OSM tags, the OSM id, type, version and timestamp.
- Run it on a local file: `python osm.py --local FILE.osm.pbf OUT_DIR`.

### Licence of the OSM data

- The OSM data is under the Open Database Licence 1.0 (ODbL). Credit: "© OpenStreetMap contributors"
  (https://www.openstreetmap.org/copyright).
- Keep the OSM data in its own tables, with its own source field. Do not mix it into government records without a label.
- A public database that holds the OSM data together with other data must be shared under the ODbL.
