# Last Voyage

A living tracker of the world's ship-breaking: every large ocean-going ship sent for scrap since 2012, broken down by where it was broken, who owned it, the flag it flew, its type and its age.

The site is static (`docs/`). A scheduled GitHub Action keeps its data current, so nobody has to maintain it by hand.

## How it works

```
shipbreakingplatform.org/annual-lists/   (one .xlsx per year, 2012 →)
        │  scripts/fetch.py   finds the links on the page, downloads new or corrected files
        ▼
data/raw/<year>.xlsx  (not committed)  +  data/sources.json  (URL, sha256, date fetched)
        │  scripts/parse.py   normalises 14 differently-shaped workbooks into one table
        ▼
data/ships.csv                                (one row per ship)
        │  scripts/build.py   aggregates, runs sanity checks
        ▼
docs/data/stats.json  +  docs/data/ships.json → docs/index.html (the site)
```

`.github/workflows/update.yml` runs every Monday, and on demand from the **Actions** tab. It re-runs the pipeline. If a new or corrected list was published, it commits the updated data and redeploys the site. If nothing changed, it just redeploys the current site. A keep-alive step stops GitHub from disabling the schedule after 60 days without commits.

If the source page changes layout, or a list parses badly (e.g. fewer than 100 ships in a year, or missing columns), the run **fails without publishing** and GitHub emails the repo owner. The live site keeps showing the last good data.

## One-time setup

1. Push this repo to GitHub.
2. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
3. **Actions tab → "Refresh data and deploy" → Run workflow** (or just push to `main`).

The site will be at `https://<owner>.github.io/<repo>/`.

## Run locally

```bash
pip install -r requirements.txt
python scripts/fetch.py      # download the lists into data/raw/
python scripts/build.py      # parse + aggregate → docs/data/
python -m http.server -d docs 8000   # open http://localhost:8000
```

## Data notes

- **Source:** [NGO Shipbreaking Platform](https://shipbreakingplatform.org/annual-lists/) annual lists. Last Voyage is independent and not affiliated with the Platform. The lists carry a disclaimer but no explicit reuse licence, so the original files are not redistributed here: they are downloaded at build time, and only derived tables are published, with attribution on every page.
- **Validated:** parsed totals match the Platform's own press releases (2015: 469 of 768 ships broken in South Asia; 2024: 409 ships, 255 in South Asia).
- **Metrics we deliberately don't show**, because they aren't consistent across the period:
  - scrap price ($/LDT): only in the 2012–13 lists;
  - light displacement tonnage: missing for 2014–17;
  - wrecks and total losses: no open, automatable source;
  - world-fleet share: UNCTAD's data is behind a bot wall or an undocumented API.
- **Gross tonnage** is shown from 2014 onwards only, because the 2012–13 lists don't report it.
- **Ship types:** the source uses 300+ free-text labels. `CATEGORY_RULES` in `scripts/parse.py` maps them to eight families.
- **Country names** are normalised with `COUNTRY_ALIASES` in `scripts/parse.py`. If a new spelling shows up in a future list, add it there.
