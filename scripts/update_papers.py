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
try:
    import fitz
except ImportError:
    fitz = None

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "public" / "data" / "papers.json"
FIGURE_DIR = ROOT / "public" / "data" / "figures"
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

MOJIBAKE = {
    "moir\u8305": "moiré",
    "Sierpi\u8245ski": "Sierpiński",
    "\u922d?": "−",
    "\u9225?": "–",
    "\u9225": "'",
    "\u63b3": "°",
    "\u8c13": "ν",
    "\u80c3": "θ",
    "\u6e2d": "μ",
    "\u8796": "Δ",
    "\u87fa": "π",
    "\u87fd": "σ",
    "\u4f2a": "α",
    "\u8795": "Γ",
    "\u87ff": "τ",
    "\u8245": "ń",
    "\u5364": "±",
}

BAD_IMAGE_RE = re.compile(r"(arxiv-logo|ar5iv_card|favicon)", re.I)

def repair_text(text: str) -> str:
    for bad, good in MOJIBAKE.items():
        text = text.replace(bad, good)
    return (text
        .replace("moir?", "moiré")
        .replace("Sierpi?ski", "Sierpiński")
        .replace("$?_{xy}", "$\\sigma_{xy}")
        .replace("$?_z", "$\\tau_z")
        .replace("$?/3", "$\\pi/3")
        .replace("$?=1/3", "$\\nu=1/3")
        .replace("?=1/3", "ν=1/3")
        .replace("?=2/3", "ν=2/3")
        .replace("$?-$\\mathcal{T}_{3}$", "$\\alpha$-$\\mathcal{T}_{3}$")
        .replace("$?=1/\\sqrt{2}$", "$\\alpha=1/\\sqrt{2}$")
        .replace("$?=1$", "$\\alpha=1$")
        .replace("$?_{xy}", "$\\sigma_{xy}")
        .replace("60?in-plane", "60° in-plane"))

def clean(value: str | None) -> str:
    text = BeautifulSoup(html.unescape(value or ""), "lxml").get_text(" ")
    return repair_text(re.sub(r"\s+", " ", text)).strip()

def classify(title: str, abstract: str) -> str:
    text = f"{title} {abstract}".lower().replace("−", "-")
    for label, words in TAXONOMY:
        if any(word in text for word in words): return label
    return "Other_New_Materials"

def summarize_paper(title: str, abstract: str, material_system: str) -> str:
    text = clean(abstract)
    if not text:
        return "No abstract is available, so the summary is limited to the title and metadata."
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 30]
    lead = sentences[0] if sentences else text[:260]
    finding = next((s for s in sentences if re.search(r"\b(show|shows|find|finds|demonstrate|demonstrates|reveal|reveals|propose|proposes|construct|constructs|identify|identifies)\b", s, re.I)), "")
    impact = next((s for s in sentences if re.search(r"\b(provide|provides|suggest|suggests|support|supports|enable|enables|route|platform|signature|fingerprint)\b", s, re.I)), "")
    pieces = [lead]
    for sentence in (finding, impact):
        if sentence and sentence not in pieces:
            pieces.append(sentence)
    summary = " ".join(pieces)
    if len(summary) > 620:
        summary = summary[:620].rsplit(" ", 1)[0] + "..."
    label = material_system.replace("_", " ")
    return f"In {label}, this paper argues that {summary[0].lower() + summary[1:]}"

def ai_assisted_abstract(title: str, ai_summary: str) -> str:
    basis = clean(ai_summary)
    if basis and not basis.startswith("No abstract is available"):
        return f"AI-assisted abstract based on the title and available metadata: {basis}"
    return f"AI-assisted abstract based on the title and available metadata: This paper studies {clean(title)} in the context of quantum anomalous Hall or Chern-insulator research. The current metadata source does not provide an original abstract, so this text is provided only as a reading aid."

def date_parts(item: dict) -> str:
    for key in ("published-print", "published-online", "published", "issued", "created"):
        parts = item.get(key, {}).get("date-parts", [[]])[0]
        if parts:
            return "-".join(str(x).zfill(2) for x in parts)
    return ""

def get_images(url: str, arxiv_id: str | None = None, limit: int = 12) -> list[str]:
    candidates = [f"https://ar5iv.labs.arxiv.org/html/{arxiv_id}"] if arxiv_id else []
    candidates.append(url)
    images: list[str] = []
    for page in candidates:
        try:
            soup = BeautifulSoup(SESSION.get(page, timeout=12).text, "lxml")
            nodes = list(soup.select("figure img, img.figure, img"))
            meta = soup.select_one('meta[property="og:image"], meta[name="twitter:image"]')
            if meta:
                nodes.insert(0, meta)
            for node in nodes:
                image = node.get("content") or node.get("src") or node.get("data-src")
                if not image or BAD_IMAGE_RE.search(image):
                    continue
                image = requests.compat.urljoin(page, image)
                if image not in images:
                    images.append(image)
                if len(images) >= limit:
                    return images
        except requests.RequestException:
            pass
    return images

def get_image(url: str, arxiv_id: str | None = None) -> str | None:
    images = get_images(url, arxiv_id, limit=1)
    return images[0] if images else None

def extract_captions_from_text(text: str, limit: int = 12) -> list[str]:
    text = repair_text(re.sub(r"\s+", " ", text))
    pattern = re.compile(r"((?:Fig\.|Figure)\s+\d+[A-Za-z]?\s*[.:].*?)(?=\s+(?:Fig\.|Figure)\s+\d+[A-Za-z]?\s*[.:]|\s+References\b|\s+Acknowledg|$)", re.I)
    captions = []
    for match in pattern.finditer(text):
        caption = match.group(1).strip()
        if len(caption) < 20:
            continue
        if len(caption) > 900:
            caption = caption[:900].rsplit(" ", 1)[0] + "..."
        captions.append(caption)
        if len(captions) >= limit:
            break
    return captions

def get_arxiv_pdf(arxiv_id: str):
    response = SESSION.get(f"https://export.arxiv.org/pdf/{arxiv_id}", timeout=45)
    response.raise_for_status()
    return fitz.open(stream=response.content, filetype="pdf")

def extract_arxiv_pdf_captions(arxiv_id: str, limit: int = 12) -> list[str]:
    if fitz is None:
        return []
    try:
        doc = get_arxiv_pdf(arxiv_id)
        text = "\n".join(page.get_text("text") for page in doc[:min(12, len(doc))])
        return extract_captions_from_text(text, limit=limit)
    except Exception as exc:
        logging.debug("PDF caption extraction failed for %s: %s", arxiv_id, exc)
    return []

def extract_arxiv_pdf_figures(arxiv_id: str, limit: int = 12) -> list[str]:
    """Extract likely paper figures from the first pages of an arXiv PDF."""
    if fitz is None: return []
    stem = f"arxiv-{arxiv_id.replace('/', '_')}"
    existing = sorted(FIGURE_DIR.glob(f"{stem}-fig*.png"))
    legacy = FIGURE_DIR / f"{stem}.png"
    if existing:
        return [f"/data/figures/{path.name}" for path in existing[:limit]]
    try:
        doc = get_arxiv_pdf(arxiv_id)
        candidates = []
        seen_xrefs = set()
        for page_index in range(min(8, len(doc))):
            page = doc[page_index]
            images = page.get_images(full=True)
            if not images: continue
            for img in images:
                xref = img[0]
                if xref in seen_xrefs:
                    continue
                seen_xrefs.add(xref)
                pix = fitz.Pixmap(doc, xref)
                if pix.width < 240 or pix.height < 160: continue
                ratio = pix.width / pix.height
                if ratio < 0.25 or ratio > 4: continue
                score = (pix.width * pix.height) / (1 + page_index * 0.18)
                candidates.append((score, page_index, xref))
        if candidates:
            FIGURE_DIR.mkdir(parents=True, exist_ok=True)
            saved = []
            for index, (_, _, xref) in enumerate(sorted(candidates, reverse=True)[:limit], start=1):
                target = FIGURE_DIR / f"{stem}-fig{index:02d}.png"
                pix = fitz.Pixmap(doc, xref)
                if pix.alpha or pix.colorspace != fitz.csRGB:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                pix.save(str(target))
                saved.append(f"/data/figures/{target.name}")
            return saved
    except Exception as exc:
        logging.debug("PDF figure extraction failed for %s: %s", arxiv_id, exc)
    if legacy.exists():
        return [f"/data/figures/{legacy.name}"]
    return []

def extract_arxiv_pdf(arxiv_id: str) -> str | None:
    figures = extract_arxiv_pdf_figures(arxiv_id, limit=1)
    return figures[0] if figures else None

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
        figure_urls = extract_arxiv_pdf_figures(aid) or get_images(e.id, aid)
        figure_captions = extract_arxiv_pdf_captions(aid, limit=len(figure_urls))
        image = figure_urls[0] if figure_urls else None
        material_system = classify(title, abstract)
        results.append({"id": f"arxiv:{aid}", "title": title, "authors": [clean(a.name) for a in e.authors], "abstract": abstract, "journal": "arXiv", "published": published.date().isoformat(), "url": f"https://arxiv.org/abs/{aid}", "doi": getattr(e, "arxiv_doi", None), "source": "arXiv", "material_system": material_system, "image_url": image, "figure_urls": figure_urls, "figure_captions": figure_captions, "ai_summary": summarize_paper(title, abstract, material_system)})
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
        figure_urls = get_images(url)
        material_system = classify(title, abstract)
        results.append({"id": f"doi:{doi}", "title": title, "authors": authors, "abstract": abstract, "journal": clean((item.get("container-title") or ["Journal article"])[0]), "published": date_parts(item), "url": url, "doi": doi, "source": "Crossref", "material_system": material_system, "image_url": figure_urls[0] if figure_urls else None, "figure_urls": figure_urls, "figure_captions": [], "ai_summary": summarize_paper(title, abstract, material_system)})
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
                figure_urls = get_images(link) if link else []
                material_system = classify(title, abstract)
                results.append({"id": f"rss:{hashlib.sha1(link.encode()).hexdigest()}", "title": title, "authors": [], "abstract": abstract, "journal": clean(parsed.feed.get("title", "Publisher RSS")), "published": published, "url": link, "doi": None, "source": "Publisher RSS", "material_system": material_system, "image_url": figure_urls[0] if figure_urls else None, "figure_urls": figure_urls, "figure_captions": [], "ai_summary": summarize_paper(title, abstract, material_system)})
        except requests.RequestException as exc:
            logging.warning("RSS feed failed (%s): %s", feed_url, exc)
    return results

def merge(new: list[dict]) -> dict:
    try: old = json.loads(DB_PATH.read_text(encoding="utf-8")).get("papers", [])
    except (FileNotFoundError, json.JSONDecodeError): old = []
    records = {p["id"]: p for p in old}
    for paper in new:
        previous = records.get(paper["id"], {})
        previous_figures = [x for x in previous.get("figure_urls", []) if not BAD_IMAGE_RE.search(x)]
        if not paper.get("figure_urls"):
            paper["figure_urls"] = previous_figures
        if not paper.get("figure_captions"):
            paper["figure_captions"] = previous.get("figure_captions", [])
        if not paper.get("abstract") and previous.get("abstract"):
            paper["abstract"] = previous.get("abstract")
            paper["abstract_status"] = previous.get("abstract_status", "original")
        elif not paper.get("abstract"):
            paper["abstract"] = ai_assisted_abstract(paper.get("title", ""), paper.get("ai_summary", ""))
            paper["abstract_status"] = "ai_assisted"
        else:
            paper["abstract_status"] = paper.get("abstract_status") or previous.get("abstract_status") or "original"
        if not paper.get("ai_summary"):
            paper["ai_summary"] = previous.get("ai_summary") or summarize_paper(paper.get("title", ""), paper.get("abstract", ""), paper.get("material_system", "Other_New_Materials"))
        if not paper.get("image_url") or BAD_IMAGE_RE.search(str(paper.get("image_url"))):
            paper["image_url"] = (paper.get("figure_urls") or [None])[0] or previous.get("image_url")
        if paper.get("image_url") and BAD_IMAGE_RE.search(str(paper.get("image_url"))):
            paper["image_url"] = None
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
