"""
News Scraper — multi-source headline aggregator with a small Flask website + PWA shell.

Sources:
  - CNN World         (https://edition.cnn.com/world)
  - The Daily Star     (https://www.thedailystar.net)
  - Prothom Alo (English) (https://en.prothomalo.com)

Design notes:
  - Each source has its own scraper function that returns a list of dicts:
    {"title": str, "url": str, "source": str}
  - Results are cached in-memory for CACHE_MINUTES so repeated page loads
    don't hammer the target sites. Hit /refresh (or the Refresh button) to
    force a re-scrape.
  - Site markup changes over time — if a source stops returning results,
    the selectors in its scrape_* function are the first place to check.
"""

from flask import Flask, render_template, send_file, jsonify, request
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import csv
import io
import threading

app = Flask(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
REQUEST_TIMEOUT = 10
CACHE_MINUTES = 10

_cache_lock = threading.Lock()
_cache = {
    "headlines": [],
    "fetched_at": None,
    "errors": [],
}


# ---------------------------------------------------------------------------
# Individual source scrapers
# ---------------------------------------------------------------------------

def scrape_cnn():
    url = "https://edition.cnn.com/world"
    items = []
    res = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    seen = set()
    for tag in soup.find_all("a"):
        title = tag.get_text(strip=True)
        link = tag.get("href")
        if title and link and "/202" in link:
            full_link = f"https://edition.cnn.com{link}" if link.startswith("/") else link
            key = (title, full_link)
            if key not in seen:
                seen.add(key)
                items.append({"title": title, "url": full_link, "source": "CNN"})
    return items


def scrape_daily_star():
    url = "https://www.thedailystar.net"
    items = []
    res = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    seen = set()
    for tag in soup.find_all("a", href=True):
        title = tag.get_text(strip=True)
        link = tag["href"]
        # Daily Star article URLs contain /news/ followed by a slug ending in a numeric id
        if title and len(title) > 15 and "/news/" in link:
            full_link = f"https://www.thedailystar.net{link}" if link.startswith("/") else link
            key = (title, full_link)
            if key not in seen:
                seen.add(key)
                items.append({"title": title, "url": full_link, "source": "The Daily Star"})
    return items


def scrape_prothom_alo():
    url = "https://en.prothomalo.com"
    items = []
    res = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    seen = set()
    for tag in soup.find_all("a", href=True):
        title = tag.get_text(strip=True)
        link = tag["href"]
        if title and len(title) > 15 and "/" in link.strip("/"):
            full_link = f"https://en.prothomalo.com{link}" if link.startswith("/") else link
            if "en.prothomalo.com" not in full_link:
                continue
            key = (title, full_link)
            if key not in seen:
                seen.add(key)
                items.append({"title": title, "url": full_link, "source": "Prothom Alo"})
    return items


SOURCES = {
    "CNN": scrape_cnn,
    "The Daily Star": scrape_daily_star,
    "Prothom Alo": scrape_prothom_alo,
}


# ---------------------------------------------------------------------------
# Aggregation + caching
# ---------------------------------------------------------------------------

def fetch_all(force=False):
    with _cache_lock:
        fresh = (
            _cache["fetched_at"]
            and datetime.now() - _cache["fetched_at"] < timedelta(minutes=CACHE_MINUTES)
        )
        if fresh and not force:
            return _cache["headlines"], _cache["errors"]

        all_items = []
        errors = []
        for name, scraper in SOURCES.items():
            try:
                all_items.extend(scraper())
            except Exception as exc:  # network hiccups / markup changes shouldn't kill the page
                errors.append(f"{name}: {exc}")

        _cache["headlines"] = all_items
        _cache["fetched_at"] = datetime.now()
        _cache["errors"] = errors
        return all_items, errors


def save_headlines_to_csv(headlines):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Source", "Headline", "URL"])
    for item in headlines:
        writer.writerow([item["source"], item["title"], item["url"]])
    output.seek(0)
    return output


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    headlines, errors = fetch_all()
    source_filter = request.args.get("source", "all")
    q = request.args.get("q", "").strip().lower()

    filtered = headlines
    if source_filter != "all":
        filtered = [h for h in filtered if h["source"] == source_filter]
    if q:
        filtered = [h for h in filtered if q in h["title"].lower()]

    return render_template(
        "index.html",
        headlines=filtered,
        sources=list(SOURCES.keys()),
        active_source=source_filter,
        query=q,
        fetched_at=_cache["fetched_at"],
        errors=errors,
        total=len(filtered),
    )


@app.route("/refresh")
def refresh():
    fetch_all(force=True)
    return home()


@app.route("/download")
def download_csv():
    headlines, _ = fetch_all()
    source_filter = request.args.get("source", "all")
    if source_filter != "all":
        headlines = [h for h in headlines if h["source"] == source_filter]

    csv_file = save_headlines_to_csv(headlines)
    date = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"news_headlines_{date}.csv"
    return send_file(
        io.BytesIO(csv_file.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
    )


@app.route("/api/headlines")
def api_headlines():
    headlines, errors = fetch_all()
    return jsonify({"count": len(headlines), "headlines": headlines, "errors": errors})


@app.route("/manifest.json")
def manifest():
    return app.send_static_file("manifest.json")


@app.route("/service-worker.js")
def service_worker():
    # served from root scope so it can control the whole site
    return app.send_static_file("service-worker.js")


if __name__ == "__main__":
    app.run(debug=True)
