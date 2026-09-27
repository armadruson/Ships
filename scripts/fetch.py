"""Download the NGO Shipbreaking Platform annual lists into data/raw/<year>.xlsx.

File URLs move when the Platform re-uploads a corrected list, so links are
always discovered from the listing page instead of being hard-coded.
The raw files are not kept in git: every run downloads them afresh, and
data/sources.json (URL + sha256) records which version the site was built from.
"""
import gzip
import hashlib
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
MANIFEST = ROOT / "data" / "sources.json"
LISTING = "https://shipbreakingplatform.org/annual-lists/"
LINK = re.compile(r'href="([^"]*?/((?:19|20)\d\d)-List-of-all-ships[^"]*?\.xlsx)"', re.I)
UA = "LastVoyage-DataBot/1.0 (+https://github.com; annual refresh of public ship-breaking lists)"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    # The site gzips responses even when not asked to.
    return gzip.decompress(data) if data[:2] == b"\x1f\x8b" else data


def main():
    html = get(LISTING).decode("utf-8", "replace")
    links = {}
    for url, year in LINK.findall(html):
        links.setdefault(int(year), url.replace("&amp;", "&"))
    if not links:
        sys.exit("fetch: no list links found; the listing page layout probably changed")

    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    RAW.mkdir(parents=True, exist_ok=True)
    changed = []
    for year, url in sorted(links.items()):
        entry = manifest.get(str(year), {})
        path = RAW / f"{year}.xlsx"
        data = get(url)
        if not data.startswith(b"PK"):
            print(f"fetch: {year}: not an xlsx, skipped ({url})")
            continue
        path.write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        if entry.get("sha256") != digest:
            changed.append(year)
            manifest[str(year)] = {"url": url, "sha256": digest, "fetched": date.today().isoformat()}
        elif entry.get("url") != url:  # same file re-uploaded elsewhere
            manifest[str(year)] = {**entry, "url": url}

    MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print(f"fetch: {len(links)} lists online, updated: {changed or 'none'}")


if __name__ == "__main__":
    main()
