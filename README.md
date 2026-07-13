# News Scraper

📰 A lightweight news aggregator — scrapes live headlines from **CNN World**, **The Daily Star**, and **Prothom Alo (English)**, and serves them as an installable web app (PWA).

## Features

- 🔍 Scrapes real-time headlines from 3 sources in parallel
- 🗂️ Filter by source (tabs) and search by keyword
- 📋 Clean, mobile-friendly dark UI
- 💾 Download headlines as CSV (filtered by source if selected)
- 🔁 Manual refresh + 10-minute in-memory cache (so the site doesn't hammer the source sites on every page load)
- 📲 **Installable as an app** on phone or desktop (PWA — add to home screen, works offline for the app shell)
- 🔌 `/api/headlines` JSON endpoint if you want to consume the data elsewhere

## Tech Stack

- Python 3 + Flask
- BeautifulSoup4 + Requests
- Vanilla HTML/CSS/JS (no build step)
- Service Worker + Web App Manifest for PWA install support

## Setup

```bash
pip install -r requirements.txt
python app.py
```

Then open `http://localhost:5000` in your browser. On mobile Chrome/Safari, open the same URL and use "Add to Home Screen" / the install prompt to install it as an app.

> **Note:** the install prompt (`beforeinstallprompt`) only fires over **HTTPS** (or `localhost`). If you deploy this, make sure it's served over HTTPS — most hosts (Render, Railway, Fly.io, PythonAnywhere) give you this for free.

## Project structure

```
news_scraper/
├── app.py                  # Flask app: scrapers, caching, routes
├── requirements.txt
├── templates/
│   └── index.html          # Main page (tabs, search, headline list)
└── static/
    ├── manifest.json       # PWA manifest
    ├── service-worker.js   # Offline shell caching
    └── icons/
        ├── icon-192.png
        └── icon-512.png
```

## Adding another news source

1. Write a `scrape_yoursite()` function in `app.py` that returns a list of
   `{"title": ..., "url": ..., "source": "Your Site"}` dicts.
2. Add it to the `SOURCES` dict.
3. That's it — it automatically appears as a new tab and is included in
   `/download`, `/api/headlines`, and search.

## A note on scraping reliability

News sites frequently change their HTML structure. If a source stops
returning headlines, check its `scrape_*()` function in `app.py` — the
selectors may need updating. The Daily Star and Prothom Alo scrapers were
written from their general page structure and should be spot-checked after
your first run, since I couldn't hit their live pages from this environment
to verify selectors directly.
