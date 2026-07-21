# QAHE Paper Radar

A GitHub Pages site that tracks recent quantum anomalous Hall effect and Chern-insulator papers.

The site is built with Next.js static export. Paper metadata is stored in `public/data/papers.json`, figures are stored under `public/data/figures`, and GitHub Actions rebuilds and deploys the site.

## Local Development

```bash
python -m pip install -r requirements.txt
npm install
npm run dev
```

Open `http://localhost:3000`.

## Update Papers

```bash
python scripts/update_papers.py
```

The updater collects recent papers from arXiv, Crossref, and optional publisher RSS feeds. It also extracts available PDF figures, figure captions, and local AI-style summaries from the article metadata and abstracts.

## GitHub Pages Deployment

1. Push changes to the `main` branch.
2. In the GitHub repository, open Settings -> Pages.
3. Set Source to GitHub Actions.
4. Run the `Update papers and deploy` workflow manually, or wait for the scheduled run.

For this repository, Next.js uses the GitHub Pages base path automatically during GitHub Actions builds, so generated assets resolve under `/qahe-paper-radar/`.
