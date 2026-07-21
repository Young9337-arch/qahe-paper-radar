#!/usr/bin/env python3
"""Fetch recent QAHE literature and merge it into the static JSON database."""
from __future__ import annotations

import hashlib, html, json, logging, os, re, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import feedparser
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "public" / "data" / "papers.json"
UA = os.getenv("CONTACT_EMAIL", "qahe-radar@example.com")
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": f"QAHE-Paper-Radar/1.0 (mailto:{UA})", "Accept": "text/html,application/json,application/atom+xml"})
TERMS = ["QAHE", '"quantum anomalous Hall"', '"Chern insulator"', '"quantized Hall"']
TAXONOMY = [
    ("MnBi2Te4_MTI", ["mnb i2te4".replace(" ", ""), "mnbi4te7", "magnetic topological insulator", "cr-doped", "v-doped", "tetradymite", "bi2se3", "bi2te3"]),
    ("Moire_Superlattice", ["moire", "moiré", "twisted bilayer", "twisted graphene", "tblg", "tmote2", "wse2", "transition metal dichalcogenide", "tmd homobilayer"]),
    ("Kagome_Lattice", ["kagome", "fesn", "co3sn2s2", "csv3sb5", "rmn6sn6"]),
    ("Oxide_Heterostructure", ["oxide", "srruo3", "euo", "yig", "heterostructure", "interface", "lao/sto"]),
]

def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", BeautifulSoup(html.unescape(value or ""), "lxml").get_text(" ")).strip()

def classify(title: str, abstract: str) -> str:
    text = f"{title} {abstract}".lower().replace("−", "-")
    for label, words in TAXONOMY:
        if any(word in text for word in words): return label
    return "Other_New_Materials"

def date_parts(item: dict) -> str:
    for key in ("published-print", "published-online", "published", "issued", "created"):
        parts = item.get(key, {}).get("date-parts", [[]])[0]
        if parts:
            return "-".join(str(x).zfill(2) for x in parts)
    return ""

def get_image(url: str, arxiv_id: str | None = None) -> str | None:
    candidates = [f"https://ar5iv.labs.arxiv.org/html/{arxiv_id}"] if arxiv_id else []
    candidates.append(url)
    for page in candidates:
        try:
            soup = BeautifulSoup(SESSION.get(page, timeout=12).text, "lxml")
            meta = soup.select_one('meta[property="og:image"], meta[name="twitter:image"]')
            image = meta.get("content") if meta else None
            if not image:
                figure = soup.select_one("figure img")
                image = figure.get("src") if figure else None
            if image and not any(x in image.lower() for x in ("arxiv-logo", "ar5iv_card", "favicon")):
                return requests.compat.urljoin(page, image)
        except requests.RequestException:
            pass
    return None

def fetch_arxiv() -> list[dict]:
    cats = " OR ".join(f"cat:{c}" for c in ["cond-mat.mes-hall", "cond-mat.str-el", "cond-mat.mtrl-sci"])
    words = " OR ".join(f"all:{t}" for t in TERMS)
    url = f"https://export.arxiv.org/api/query?search_query={quote(f'({words}) AND ({cats})')}&start=0&max_results=100&sortBy=submittedDate&sortOrder=descending"
    feed = feedparser.parse(SESSION.get(url, timeout=30).content)
    results = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    for e in feed.entries:
        published = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
        if published < cutoff: continue
        aid = e.id.rsplit("/", 1)[-1].split("v")[0]
        abstract, title = clean(e.summary), clean(e.title)
        results.append({"id": f"arxiv:{aid}", "title": title, "authors": [clean(a.name) for a in e.authors], "abstract": abstract, "journal": "arXiv", "published": published.date().isoformat(), "url": f"https://arxiv.org/abs/{aid}", "doi": getattr(e, "arxiv_doi", None), "source": "arXiv", "material_system": classify(title, abstract), "image_url": get_image(e.id, aid)})
    return results

def fetch_crossref() -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()
    rows = {}
    for term in TERMS[1:]:
        params = {"query.bibliographic": term.replace('"', ''), "filter": f"from-online-pub-date:{since}", "sort": "published", "order": "desc", "rows": 50, "select": "DOI,title,author,abstract,container-title,published-online,published-print,published,issued,created,URL,type"}
        try:
            data = SESSION.get("https://api.crossref.org/works", params=params, timeout=30).json()
            for item in data["message"]["items"]:
                doi = item.get("DOI", "").lower()
                title = clean((item.get("title") or [""])[0]); abstract = clean(item.get("abstract"))
                relevance = f"{title} {abstract}".lower()
                if doi and any(x in relevance for x in ["quantum anomalous hall", "chern insulator", "quantized hall", "qahe"]): rows[doi] = item
        except (requests.RequestException, KeyError, ValueError) as exc:
            logging.warning("Crossref query failed: %s", exc)
        time.sleep(0.2)
    results = []
    for doi, item in rows.items():
        title, abstract = clean(item["title"][0]), clean(item.get("abstract"))
        url = item.get("URL") or f"https://doi.org/{doi}"
        authors = [clean(" ".join(filter(None, [a.get("given"), a.get("family")]))) for a in item.get("author", [])]
        results.append({"id": f"doi:{doi}", "title": title, "authors": authors, "abstract": abstract, "journal": clean((item.get("container-title") or ["Journal article"])[0]), "published": date_parts(item), "url": url, "doi": doi, "source": "Crossref", "material_system": classify(title, abstract), "image_url": get_image(url)})
    return results

def fetch_publisher_rss() -> list[dict]:
    """Optionally ingest publisher feeds (comma-separated RSS_FEEDS env var).

    Keeping feeds configurable avoids hard-coding publisher URL changes while
    still supporting APS/Nature/ACS/Wiley feeds supplied by a deployment.
    """
    feeds = [x.strip() for x in os.getenv("RSS_FEEDS", "").split(",") if x.strip()]
    results = []
    for feed_url in feeds:
        try:
            parsed = feedparser.parse(SESSION.get(feed_url, timeout=20).content)
            for e in parsed.entries:
                title, abstract = clean(getattr(e, "title", "")), clean(getattr(e, "summary", ""))
                text = f"{title} {abstract}".lower()
                if not any(k.strip('"').lower() in text for k in TERMS): continue
                link = getattr(e, "link", "")
                published = getattr(e, "published", "")[:10]
                results.append({"id": f"rss:{hashlib.sha1(link.encode()).hexdigest()}", "title": title, "authors": [], "abstract": abstract, "journal": parsed.feed.get("title", "Publisher RSS"), "published": published, "url": link, "doi": None, "source": "Publisher RSS", "material_system": classify(title, abstract), "image_url": get_image(link) if link else None})
        except requests.RequestException as exc:
            logging.warning("RSS feed failed (%s): %s", feed_url, exc)
    return results

def merge(new: list[dict]) -> dict:
    try: old = json.loads(DB_PATH.read_text(encoding="utf-8")).get("papers", [])
    except (FileNotFoundError, json.JSONDecodeError): old = []
    records = {p["id"]: p for p in old}
    for paper in new:
        previous = records.get(paper["id"], {})
        if not paper.get("image_url"): paper["image_url"] = previous.get("image_url")
        records[paper["id"]] = paper
    papers = sorted(records.values(), key=lambda p: p.get("published", ""), reverse=True)
    return {"updated_at": datetime.now(timezone.utc).isoformat(), "papers": papers}

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    papers = []
    for name, fetcher in (("arXiv", fetch_arxiv), ("Crossref", fetch_crossref), ("Publisher RSS", fetch_publisher_rss)):
        try:
            found = fetcher(); papers.extend(found); logging.info("%s: %d papers", name, len(found))
        except Exception as exc:
            logging.exception("%s failed without aborting the update: %s", name, exc)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    DB_PATH.write_text(json.dumps(merge(papers), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__": main()
