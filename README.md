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
